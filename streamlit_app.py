import streamlit as st
import requests
import json
import re
import pandas as pd
from datetime import datetime
import time

# Page configuration
st.set_page_config(
    page_title="Content Analyzer",
    page_icon="🎯",
    layout="wide"
)

# CSS
st.markdown("""
<style>
.main-header {
    text-align: center;
    padding: 2rem 0;
    margin-bottom: 2rem;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-radius: 15px;
}
.score-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 2rem;
    border-radius: 15px;
    text-align: center;
    margin: 1rem 0;
}
.component-card {
    background: white;
    padding: 1.2rem;
    border-radius: 8px;
    border-left: 4px solid #667eea;
    margin: 0.5rem 0;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
</style>
""", unsafe_allow_html=True)

# Session state
if 'analysis_history' not in st.session_state:
    st.session_state.analysis_history = []
if 'selected_category' not in st.session_state:
    st.session_state.selected_category = 'heartwarming'

# Categories
CATEGORIES = {
    'heartwarming': {
        'name': 'Heartwarming Content',
        'emoji': '❤️',
        'keywords': ['reunion', 'surprise', 'family', 'love', 'touching', 'heartwarming', 'emotional', 'beautiful'],
        'emotions': ['crying', 'tears', 'emotional', 'touched', 'moving', 'beautiful', 'sweet', 'precious'],
        'positive_auth': ['genuine', 'real', 'spontaneous', 'unexpected'],
        'negative_auth': ['fake', 'staged', 'acting', 'scripted']
    },
    'motivational': {
        'name': 'Motivational Content', 
        'emoji': '💪',
        'keywords': ['motivation', 'inspiring', 'success', 'achievement', 'transformation', 'overcome'],
        'emotions': ['motivated', 'inspired', 'pumped', 'determined', 'powerful', 'life changing'],
        'positive_auth': ['struggle', 'journey', 'earned', 'dedication'],
        'negative_auth': ['overnight success', 'easy money', 'secret', 'hack']
    },
    'traumatic': {
        'name': 'Traumatic Events',
        'emoji': '⚠️', 
        'keywords': ['tragedy', 'disaster', 'accident', 'emergency', 'crisis', 'breaking news'],
        'emotions': ['shocked', 'devastating', 'tragic', 'prayers', 'heart goes out'],
        'positive_auth': ['breaking news', 'official', 'witness', 'survivor'],
        'negative_auth': ['clickbait', 'sensational', 'dramatic music']
    }
}

def extract_video_id(url):
    pattern = r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)'
    match = re.search(pattern, url)
    return match.group(1) if match else None

def parse_duration(duration_str):
    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    match = re.match(pattern, duration_str)
    if not match:
        return "0:00"
    
    hours, minutes, seconds = match.groups()
    hours = int(hours) if hours else 0
    minutes = int(minutes) if minutes else 0
    seconds = int(seconds) if seconds else 0
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"

@st.cache_data(ttl=300)
def fetch_youtube_data(video_id, api_key):
    try:
        video_url = f"https://www.googleapis.com/youtube/v3/videos"
        video_params = {
            'part': 'snippet,statistics,contentDetails',
            'id': video_id,
            'key': api_key
        }
        
        video_response = requests.get(video_url, params=video_params)
        video_response.raise_for_status()
        video_data = video_response.json()
        
        if not video_data.get('items'):
            raise Exception("Video not found")
        
        video = video_data['items'][0]
        stats = video['statistics']
        snippet = video['snippet']
        content_details = video['contentDetails']
        
        # Get comments
        comments = []
        try:
            comments_url = f"https://www.googleapis.com/youtube/v3/commentThreads"
            comments_params = {
                'part': 'snippet',
                'videoId': video_id,
                'maxResults': 100,
                'order': 'relevance',
                'key': api_key
            }
            
            comments_response = requests.get(comments_url, params=comments_params)
            if comments_response.status_code == 200:
                comments_data = comments_response.json()
                for item in comments_data.get('items', []):
                    comment_text = item['snippet']['topLevelComment']['snippet']['textDisplay']
                    comments.append(comment_text)
        except:
            pass
        
        return {
            'videoId': video_id,
            'title': snippet['title'],
            'description': snippet.get('description', ''),
            'viewCount': int(stats.get('viewCount', 0)),
            'likeCount': int(stats.get('likeCount', 0)),
            'commentCount': int(stats.get('commentCount', 0)),
            'duration': parse_duration(content_details['duration']),
            'publishedAt': snippet['publishedAt'],
            'channelTitle': snippet['channelTitle'],
            'comments': comments
        }
        
    except requests.exceptions.RequestException as e:
        if e.response and e.response.status_code == 403:
            raise Exception("API key error")
        elif e.response and e.response.status_code == 429:
            raise Exception("API quota exceeded")
        else:
            raise Exception(f"Error: {str(e)}")

def analyze_sentiment(comment_text):
    comment_lower = comment_text.lower()
    positive_words = ['love', 'great', 'amazing', 'awesome', 'beautiful', 'perfect', 'crying', 'tears', 'emotional']
    negative_words = ['hate', 'terrible', 'awful', 'bad', 'fake', 'staged', 'boring']
    
    positive_count = sum(1 for word in positive_words if word in comment_lower)
    negative_count = sum(1 for word in negative_words if word in comment_lower)
    
    if positive_count > negative_count:
        return 'positive'
    elif negative_count > positive_count:
        return 'negative'
    else:
        return 'neutral'

def extract_moments(comments, category_data):
    timestamp_pattern = r'(?:at\s+)?(\d{1,2}):(\d{2})|(\d{1,2}):(\d{2})|(\d+:\d+)'
    moments = []
    
    for comment in comments:
        comment_lower = comment.lower()
        timestamps = re.findall(timestamp_pattern, comment_lower)
        
        if timestamps:
            keyword_matches = sum(1 for kw in category_data['keywords'] if kw in comment_lower)
            emotion_matches = sum(1 for em in category_data['emotions'] if em in comment_lower)
            relevance = keyword_matches * 2.0 + emotion_matches * 2.5
            
            if relevance > 0:
                for timestamp_match in timestamps:
                    timestamp = ':'.join(filter(None, timestamp_match))
                    moments.append({
                        'timestamp': timestamp,
                        'comment': comment,
                        'relevance': relevance,
                        'sentiment': analyze_sentiment(comment)
                    })
    
    return sorted(moments, key=lambda x: x['relevance'], reverse=True)

def calculate_score(data, category_key):
    category_data = CATEGORIES[category_key]
    
    # Text analysis
    title_text = data['title'].lower()
    desc_text = data['description'].lower()
    comments_text = ' '.join(data['comments']).lower()
    
    # Component scores
    keyword_score = 0.2
    emotion_score = 0.2
    authenticity_score = 0.5
    engagement_score = 0.3
    
    # Keywords
    keyword_matches = sum(1 for kw in category_data['keywords'] if kw in title_text or kw in comments_text)
    if keyword_matches > 3:
        keyword_score = 0.8
    elif keyword_matches > 1:
        keyword_score = 0.6
    elif keyword_matches > 0:
        keyword_score = 0.4
    
    # Emotions
    emotion_matches = sum(1 for em in category_data['emotions'] if em in comments_text)
    if emotion_matches > 5:
        emotion_score = 0.8
    elif emotion_matches > 2:
        emotion_score = 0.6
    elif emotion_matches > 0:
        emotion_score = 0.4
    
    # Authenticity
    positive_auth = sum(1 for auth in category_data['positive_auth'] if auth in comments_text)
    negative_auth = sum(1 for auth in category_data['negative_auth'] if auth in title_text or auth in comments_text)
    
    if positive_auth > negative_auth:
        authenticity_score = 0.8
    elif negative_auth > positive_auth:
        authenticity_score = 0.3
    else:
        authenticity_score = 0.5
    
    # Engagement
    if data['viewCount'] > 0:
        like_ratio = data['likeCount'] / data['viewCount']
        comment_ratio = data['commentCount'] / data['viewCount']
        
        if like_ratio > 0.03 or comment_ratio > 0.005:
            engagement_score = 0.8
        elif like_ratio > 0.015 or comment_ratio > 0.002:
            engagement_score = 0.6
        else:
            engagement_score = 0.4
    
    # Calculate final score based on category
    if category_key == 'heartwarming':
        base = 3.0
        final = base + (authenticity_score * 3.5 + emotion_score * 2.5 + keyword_score * 1.5 + engagement_score * 0.5)
        if authenticity_score < 0.4:
            final *= 0.6
    elif category_key == 'motivational':
        base = 2.0
        final = base + (authenticity_score * 3.0 + keyword_score * 2.5 + emotion_score * 2.0 + engagement_score * 0.5)
        if authenticity_score < 0.3:
            final *= 0.5
    else:  # traumatic
        base = 1.0
        responsibility = 0.7 if 'education' in desc_text or 'awareness' in desc_text else 0.3
        final = base + (responsibility * 4.0 + authenticity_score * 3.0 + keyword_score * 2.0 + engagement_score * 0.5)
        if responsibility < 0.5:
            final *= 0.4
    
    components = {
        'keywords': keyword_score,
        'emotions': emotion_score, 
        'authenticity': authenticity_score,
        'engagement': engagement_score
    }
    
    confidence = 0.3
    if data['title']:
        confidence += 0.2
    if len(data['comments']) > 10:
        confidence += 0.3
    if data['viewCount'] > 1000:
        confidence += 0.2
    
    return {
        'score': min(final, 10.0),
        'components': components,
        'confidence': min(confidence, 1.0),
        'authenticity': 'authentic' if authenticity_score > 0.6 else 'questionable' if authenticity_score > 0.4 else 'likely_fake'
    }

def get_color(score):
    if score >= 8:
        return "🟢"
    elif score >= 6:
        return "🟡"
    elif score >= 4:
        return "🟠"
    else:
        return "🔴"

# Main app
st.markdown("""
<div class="main-header">
    <h1>🎯 Content Analyzer</h1>
    <p>Specialized Analysis for Heartwarming, Motivational & Traumatic Content</p>
</div>
""", unsafe_allow_html=True)

# Category selection
st.subheader("Select Category")
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("❤️ Heartwarming", use_container_width=True):
        st.session_state.selected_category = 'heartwarming'

with col2:
    if st.button("💪 Motivational", use_container_width=True):
        st.session_state.selected_category = 'motivational'

with col3:
    if st.button("⚠️ Traumatic", use_container_width=True):
        st.session_state.selected_category = 'traumatic'

selected = st.session_state.selected_category
category_info = CATEGORIES[selected]
st.info(f"Selected: {category_info['emoji']} {category_info['name']}")

# Sidebar
with st.sidebar:
    st.header("Configuration")
    api_key = st.text_input("YouTube API Key", type="password")
    if not api_key:
        st.warning("API key required")

# Main analysis
st.subheader("Video Analysis")

col1, col2 = st.columns([3, 1])
with col1:
    video_url = st.text_input("YouTube URL:", placeholder="https://youtube.com/watch?v=example")
with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    analyze_btn = st.button("Analyze", disabled=not api_key or not video_url, use_container_width=True)

if analyze_btn and video_url:
    video_id = extract_video_id(video_url)
    
    if not video_id:
        st.error("Invalid URL")
    else:
        try:
            with st.spinner("Analyzing..."):
                data = fetch_youtube_data(video_id, api_key)
                result = calculate_score(data, selected)
                moments = extract_moments(data['comments'], category_info)
            
            st.success("Analysis Complete!")
            
            # Results
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"### {data['title']}")
                st.markdown(f"**Channel:** {data['channelTitle']}")
                st.markdown(f"**Duration:** {data['duration']}")
                
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("Views", f"{data['viewCount']:,}")
                with col_b:
                    st.metric("Likes", f"{data['likeCount']:,}")
                with col_c:
                    st.metric("Comments", f"{data['commentCount']:,}")
            
            with col2:
                score = result['score']
                color = get_color(score)
                
                st.markdown(f"""
                <div class="score-card">
                    <h2>{category_info['emoji']} Score</h2>
                    <h1 style="font-size: 3.5rem; margin: 0;">{score:.1f}</h1>
                    <h3>/10</h3>
                    <p>Confidence: {result['confidence']:.0%}</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Authenticity
            auth = result['authenticity']
            if auth == 'authentic':
                st.success("✅ Authentic Content")
            elif auth == 'questionable':
                st.warning("⚠️ Questionable Authenticity")
            else:
                st.error("❌ Likely Fake/Staged")
            
            # Components
            st.subheader("Component Scores")
            components = result['components']
            
            for key, value in components.items():
                component_score = value * 10
                color_emoji = get_color(component_score)
                st.markdown(f"""
                <div class="component-card">
                    <h4>{key.title()}: {color_emoji} {component_score:.1f}/10</h4>
                </div>
                """, unsafe_allow_html=True)
            
            # Moments
            if moments:
                st.subheader("Key Moments")
                for moment in moments[:3]:
                    st.write(f"⏰ **{moment['timestamp']}** - {moment['comment'][:100]}...")
            
            # Assessment
            if score >= 8.5:
                st.success("🌟 Excellent - Outstanding example")
            elif score >= 7.0:
                st.success("✅ Good - Strong category match") 
            elif score >= 5.5:
                st.info("⚠️ Moderate - Some elements present")
            else:
                st.error("❌ Poor - Does not fit category")
            
            # Save
            if st.button("Save Analysis"):
                summary = {
                    'timestamp': datetime.now().isoformat(),
                    'video_id': video_id,
                    'title': data['title'],
                    'category': selected,
                    'score': score,
                    'authenticity': auth
                }
                st.session_state.analysis_history.append(summary)
                st.success("Saved!")
            
        except Exception as e:
            st.error(f"Analysis failed: {str(e)}")

# History
if st.session_state.analysis_history:
    st.markdown("---")
    st.header("History")
    
    df = pd.DataFrame([
        {
            'Title': a['title'][:40] + '...' if len(a['title']) > 40 else a['title'],
            'Category': CATEGORIES[a['category']]['emoji'],
            'Score': f"{a['score']:.1f}",
            'Auth': a['authenticity'][:8],
            'Date': datetime.fromisoformat(a['timestamp']).strftime('%m/%d')
        }
        for a in reversed(st.session_state.analysis_history[-5:])
    ])
    
    st.dataframe(df, use_container_width=True)
    
    if st.button("Clear History"):
        st.session_state.analysis_history = []
        st.rerun()
