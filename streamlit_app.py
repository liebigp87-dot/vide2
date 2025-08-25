import streamlit as st
import requests
import json
import re
import pandas as pd
from datetime import datetime
import time
import numpy as np
from PIL import Image
import io

# Page configuration
st.set_page_config(
    page_title="Specialized Content Analyzer",
    page_icon="🎯",
    layout="wide"
)

# Custom CSS
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
    .moment-highlight {
        background: #e8f5e8;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #28a745;
        margin: 0.8rem 0;
        color: #155724;
    }
</style>
""", unsafe_allow_html=True)

# Session state
if 'analysis_history' not in st.session_state:
    st.session_state.analysis_history = []

if 'selected_category' not in st.session_state:
    st.session_state.selected_category = 'heartwarming_content'

# Category definitions
CATEGORIES = {
    'heartwarming_content': {
        'name': 'Heartwarming Content',
        'emoji': '❤️',
        'description': 'Genuine emotional moments that create positive feelings',
        'keywords': [
            'reunion', 'surprise', 'proposal', 'wedding', 'rescue', 'helping',
            'kindness', 'family', 'love', 'touching', 'heartwarming', 'wholesome',
            'emotional', 'beautiful', 'sweet', 'precious', 'blessed', 'grateful'
        ],
        'emotional_indicators': [
            'crying', 'tears', 'emotional', 'touched', 'moving', 'beautiful',
            'sweet', 'precious', 'blessed', 'grateful', 'happy tears',
            'my heart', 'feels', 'warm', 'lovely', 'amazing', 'incredible'
        ],
        'authenticity_positive': [
            'genuine', 'real', 'spontaneous', 'unexpected', 'candid', 'natural'
        ],
        'authenticity_negative': [
            'fake', 'staged', 'acting', 'scripted', 'setup', 'promotional'
        ]
    },
    
    'motivational_content': {
        'name': 'Inspiring/Motivational Content',
        'emoji': '💪',
        'description': 'Content that genuinely inspires through real achievement',
        'keywords': [
            'motivation', 'inspiring', 'success', 'achievement', 'transformation',
            'overcome', 'perseverance', 'goals', 'dreams', 'breakthrough',
            'dedication', 'discipline', 'mindset', 'hustle', 'grind', 'legend'
        ],
        'emotional_indicators': [
            'motivated', 'inspired', 'pumped', 'fired up', 'determined',
            'powerful', 'life changing', 'next level', 'beast mode',
            'unstoppable', 'goosebumps', 'chills', 'driven', 'focused'
        ],
        'authenticity_positive': [
            'years of work', 'struggle', 'journey', 'earned', 'dedication'
        ],
        'authenticity_negative': [
            'overnight success', 'easy money', 'secret', 'hack', 'simple trick'
        ]
    },
    
    'traumatic_events': {
        'name': 'Traumatic Events',
        'emoji': '⚠️',
        'description': 'Serious events with significant emotional impact',
        'keywords': [
            'tragedy', 'disaster', 'accident', 'emergency', 'crisis', 'breaking news',
            'devastating', 'shocking', 'traumatic', 'serious', 'critical', 'urgent'
        ],
        'emotional_indicators': [
            'shocked', 'devastating', 'unbelievable', 'tragic', 'terrible',
            'prayers', 'thoughts and prayers', 'heart goes out', 'so sorry',
            'hope everyone ok', 'what happened', 'can\'t believe'
        ],
        'authenticity_positive': [
            'breaking news', 'official', 'authorities', 'witness', 'survivor'
        ],
        'authenticity_negative': [
            'clickbait', 'sensational', 'dramatic music', 'views only'
        ]
    }
}

def extract_video_id(url):
    """Extract YouTube video ID from URL"""
    pattern = r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)'
    match = re.search(pattern, url)
    return match.group(1) if match else None

def parse_duration(duration_str):
    """Parse YouTube duration format"""
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
    """Fetch comprehensive YouTube data"""
    try:
        # Basic video data
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
            raise Exception("Video not found or unavailable")
        
        video = video_data['items'][0]
        stats = video['statistics']
        snippet = video['snippet']
        content_details = video['contentDetails']
        
        # Fetch comments
        comments_data = fetch_comments(video_id, api_key)
        
        # Get transcript if available
        transcript_data = get_transcript(video_id)
        
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
            'comments': comments_data['comments'],
            'sentiment': comments_data['sentiment'],
            'transcript': transcript_data
        }
        
    except requests.exceptions.RequestException as e:
        if e.response and e.response.status_code == 403:
            raise Exception("API key error: Check your YouTube Data API v3 key")
        elif e.response and e.response.status_code == 429:
            raise Exception("API quota exceeded. Try again later")
        else:
            raise Exception(f"Error: {str(e)}")

def fetch_comments(video_id, api_key, max_results=100):
    """Fetch and analyze comments"""
    comments = []
    sentiment = {'positive': 0, 'negative': 0, 'neutral': 0, 'total': 0}
    
    try:
        comments_url = f"https://www.googleapis.com/youtube/v3/commentThreads"
        comments_params = {
            'part': 'snippet',
            'videoId': video_id,
            'maxResults': max_results,
            'order': 'relevance',
            'key': api_key
        }
        
        response = requests.get(comments_url, params=comments_params)
        if response.status_code == 200:
            data = response.json()
            
            for item in data.get('items', []):
                comment_text = item['snippet']['topLevelComment']['snippet']['textDisplay']
                comments.append(comment_text)
                
                # Simple sentiment analysis
                comment_sentiment = analyze_sentiment(comment_text)
                sentiment[comment_sentiment] += 1
                sentiment['total'] += 1
    
    except Exception as e:
        st.warning(f"Limited comment access: {str(e)}")
    
    return {'comments': comments, 'sentiment': sentiment}

def get_transcript(video_id):
    """Try to get video transcript"""
    transcript_data = {'available': False, 'text': ''}
    
    try:
        # Try YouTube caption API
        caption_url = f"https://www.youtube.com/api/timedtext?lang=en&v={video_id}"
        response = requests.get(caption_url, timeout=10)
        
        if response.status_code == 200 and response.text:
            # Simple text extraction
            text_content = re.sub(r'<[^>]+>', '', response.text)
            if text_content.strip():
                transcript_data = {
                    'available': True,
                    'text': text_content.strip()
                }
    except:
        pass
    
    return transcript_data

def analyze_sentiment(comment_text):
    """Simple sentiment analysis"""
    comment_lower = comment_text.lower()
    
    positive_words = ['love', 'great', 'amazing', 'awesome', 'beautiful', 'perfect', 
                     'excellent', 'wonderful', 'fantastic', 'incredible', 'best',
                     'crying', 'tears', 'emotional', 'touching', 'moving']
    negative_words = ['hate', 'terrible', 'awful', 'bad', 'worst', 'horrible', 
                     'stupid', 'boring', 'waste', 'disappointing', 'fake', 'staged']
    
    positive_count = sum(1 for word in positive_words if word in comment_lower)
    negative_count = sum(1 for word in negative_words if word in comment_lower)
    
    if positive_count > negative_count:
        return 'positive'
    elif negative_count > positive_count:
        return 'negative'
    else:
        return 'neutral'

def extract_timestamped_moments(comments, category_data):
    """Extract timestamped moments with relevance scoring"""
    timestamp_pattern = r'(?:at\s+)?(\d{1,2}):(\d{2})|(\d{1,2}):(\d{2})|(\d+:\d+)'
    moments = []
    
    keywords = category_data['keywords']
    emotions = category_data['emotional_indicators']
    
    for comment in comments:
        comment_lower = comment.lower()
        timestamps = re.findall(timestamp_pattern, comment_lower)
        
        if timestamps:
            # Calculate relevance
            keyword_matches = sum(1 for kw in keywords if kw in comment_lower)
            emotion_matches = sum(1 for em in emotions if em in comment_lower)
            
            relevance_score = keyword_matches * 2.0 + emotion_matches * 2.5
            
            if relevance_score > 0:
                for timestamp_match in timestamps:
                    timestamp = ':'.join(filter(None, timestamp_match))
                    moments.append({
                        'timestamp': timestamp,
                        'comment': comment,
                        'relevance_score': relevance_score,
                        'sentiment': analyze_sentiment(comment)
                    })
    
    return sorted(moments, key=lambda x: x['relevance_score'], reverse=True)

def analyze_category_content(data, category_key):
    """Analyze content for specific category"""
    category_data = CATEGORIES[category_key]
    
    # Extract all text
    all_text = {
        'title': data['title'].lower(),
        'description': data['description'].lower(),
        'comments': ' '.join(data['comments']).lower(),
        'transcript': data['transcript']['text'].lower() if data['transcript']['available'] else ''
    }
    
    # Get timestamped moments
    moments = extract_timestamped_moments(data['comments'], category_data)
    
    # Category-specific analysis
    if category_key == 'heartwarming_content':
        scores = analyze_heartwarming(all_text, data, category_data, moments)
    elif category_key == 'motivational_content':
        scores = analyze_motivational(all_text, data, category_data, moments)
    elif category_key == 'traumatic_events':
        scores = analyze_traumatic(all_text, data, category_data, moments)
    else:
        scores = {'final_score': 5.0, 'components': {}, 'confidence': 0.5}
    
    return {
        'final_score': scores['final_score'],
        'component_scores': scores['components'],
        'confidence': scores['confidence'],
        'moments': moments,
        'authenticity': scores.get('authenticity', 'unknown')
    }

def analyze_heartwarming(all_text, data, category_data, moments):
    """Analyze heartwarming content"""
    
    # Component analysis
    authenticity = calculate_authenticity(all_text, category_data)
    emotional_impact = calculate_emotional_impact(data['sentiment'], all_text, category_data)
    content_match = calculate_content_match(all_text, category_data)
    viewer_response = calculate_viewer_response(moments, data['sentiment'])
    
    components = {
        'authenticity': authenticity,
        'emotional_impact': emotional_impact,
        'content_match': content_match,
        'viewer_response': viewer_response
    }
    
    # Weighted scoring
    weights = {
        'authenticity': 0.35,
        'emotional_impact': 0.30,
        'content_match': 0.20,
        'viewer_response': 0.15
    }
    
    base_score = 3.0  # Start from 3 for heartwarming
    weighted_score = sum(components[key] * weights[key] for key in weights) * 7.0
    final_score = base_score + weighted_score
    
    # Authenticity penalty
    if authenticity < 0.4:
        final_score *= 0.6
    
    # Moment bonus
    high_quality_moments = len([m for m in moments if m['relevance_score'] >= 5.0])
    if high_quality_moments >= 2:
        final_score += 1.0
    
    confidence = calculate_confidence(data, components)
    
    return {
        'final_score': min(final_score, 10.0),
        'components': components,
        'confidence': confidence,
        'authenticity': 'authentic' if authenticity > 0.7 else 'questionable' if authenticity > 0.4 else 'likely_staged'
    }

def analyze_motivational(all_text, data, category_data, moments):
    """Analyze motivational content"""
    
    # Component analysis
    authenticity = calculate_authenticity(all_text, category_data)
    achievement_evidence = calculate_achievement_evidence(all_text)
    inspirational_impact = calculate_inspirational_impact(data['sentiment'], all_text)
    actionable_value = calculate_actionable_value(all_text['transcript'])
    
    components = {
        'authenticity': authenticity,
        'achievement_evidence': achievement_evidence,
        'inspirational_impact': inspirational_impact,
        'actionable_value': actionable_value
    }
    
    # Weighted scoring
    weights = {
        'authenticity': 0.30,
        'achievement_evidence': 0.25,
        'inspirational_impact': 0.25,
        'actionable_value': 0.20
    }
    
    base_score = 2.0  # Lower start for motivational
    weighted_score = sum(components[key] * weights[key] for key in weights) * 8.0
    final_score = base_score + weighted_score
    
    # Quality bonuses and penalties
    if authenticity > 0.8 and achievement_evidence > 0.7:
        final_score += 1.0
    
    if authenticity < 0.3:
        final_score *= 0.5
    
    confidence = calculate_confidence(data, components)
    
    return {
        'final_score': min(final_score, 10.0),
        'components': components,
        'confidence': confidence,
        'authenticity': 'authentic' if authenticity > 0.7 else 'questionable' if authenticity > 0.4 else 'likely_fake'
    }

def analyze_traumatic(all_text, data, category_data, moments):
    """Analyze traumatic content"""
    
    # Component analysis
    severity = calculate_event_severity(all_text, category_data)
    responsible_handling = calculate_responsible_handling(all_text, data)
    authenticity = calculate_authenticity(all_text, category_data)
    educational_value = calculate_educational_value(all_text)
    
    components = {
        'severity': severity,
        'responsible_handling': responsible_handling,
        'authenticity': authenticity,
        'educational_value': educational_value
    }
    
    # Weighted scoring
    weights = {
        'severity': 0.25,
        'responsible_handling': 0.35,
        'authenticity': 0.25,
        'educational_value': 0.15
    }
    
    base_score = 1.0  # Very low start
    weighted_score = sum(components[key] * weights[key] for key in weights) * 9.0
    final_score = base_score + weighted_score
    
    # Responsible handling critical
    if responsible_handling < 0.5:
        final_score *= 0.4
    
    confidence = calculate_confidence(data, components)
    
    return {
        'final_score': min(final_score, 10.0),
        'components': components,
        'confidence': confidence,
        'authenticity': 'responsible' if responsible_handling > 0.7 else 'questionable' if responsible_handling > 0.4 else 'exploitative'
    }

def calculate_authenticity(all_text, category_data):
    """Calculate authenticity score"""
    score = 0.5
    
    positive_indicators = category_data['authenticity_positive']
    negative_indicators = category_data['authenticity_negative']
    
    positive_count = sum(1 for indicator in positive_indicators if indicator in all_text['comments'])
    negative_count = sum(1 for indicator in negative_indicators if indicator in all_text['title'] or indicator in all_text['comments'])
    
    if positive_count > negative_count:
        score += min(positive_count * 0.15, 0.4)
    
    if negative_count > 0:
        score -= min(negative_count * 0.2, 0.4)
    
    return max(min(score, 1.0), 0.0)

def calculate_emotional_impact(sentiment_data, all_text, category_data):
    """Calculate emotional impact"""
    score = 0.3
    
    if sentiment_data['total'] > 0:
        positive_ratio = sentiment_data['positive'] / sentiment_data['total']
        score += positive_ratio * 0.4
    
    # Strong emotional words
    strong_emotions = category_data['emotional_indicators']
    emotion_count = sum(1 for emotion in strong_emotions if emotion in all_text['comments'])
    
    if emotion_count > 5:
        score += 0.3
    elif emotion_count > 2:
        score += 0.2
    
    return min(score, 1.0)

def calculate_content_match(all_text, category_data):
    """Calculate content type match"""
    score = 0.2
    
    keyword_matches = sum(1 for kw in category_data['keywords'] if kw in all_text['title'] or kw in all_text['description'] or kw in all_text['comments'])
    
    if keyword_matches > 5:
        score += 0.6
    elif keyword_matches > 2:
        score += 0.4
    elif keyword_matches > 0:
        score += 0.2
    
    return min(score, 1.0)

def calculate_viewer_response(moments, sentiment_data):
    """Calculate viewer response quality"""
    score = 0.3
    
    if moments:
        high_quality = len([m for m in moments if m['relevance_score'] >= 5.0])
        if high_quality >= 3:
            score += 0.5
        elif high_quality >= 1:
            score += 0.3
    
    if sentiment_data['total'] > 20:
        score += 0.2
    
    return min(score, 1.0)

def calculate_achievement_evidence(all_text):
    """Calculate achievement evidence"""
    score = 0.4
    
    evidence_words = ['transformation', 'journey', 'struggle', 'overcome', 'achieved', 'success']
    matches = sum(1 for word in evidence_words if word in all_text['title'] or word in all_text['description'])
    
    if matches > 2:
        score += 0.4
    elif matches > 0:
        score += 0.2
    
    return min(score, 1.0)

def calculate_inspirational_impact(sentiment_data, all_text):
    """Calculate inspirational impact"""
    score = 0.3
    
    if sentiment_data['total'] > 0:
        positive_ratio = sentiment_data['positive'] / sentiment_data['total']
        score += positive_ratio * 0.4
    
    motivational_responses = ['motivated', 'inspired', 'pumped', 'ready']
    response_count = sum(1 for response in motivational_responses if response in all_text['comments'])
    
    if response_count > 0:
        score += 0.3
    
    return min(score, 1.0)

def calculate_actionable_value(transcript_text):
    """Calculate actionable value"""
    if not transcript_text:
        return 0.5
    
    score = 0.4
    
    actionable_phrases = ['how to', 'step', 'key is', 'important', 'advice']
    matches = sum(1 for phrase in actionable_phrases if phrase in transcript_text)
    
    if matches > 0:
        score += 0.4
    
    return min(score, 1.0)

def calculate_event_severity(all_text, category_data):
    """Calculate event severity"""
    score = 0.2
    
    severity_words = category_data['keywords']
    matches = sum(1 for word in severity_words if word in all_text['title'] or word in all_text['description'])
    
    if matches > 0:
        score += min(matches * 0.2, 0.6)
    
    return min(score, 1.0)

def calculate_responsible_handling(all_text, data):
    """Calculate responsible handling"""
    score = 0.5
    
    responsible_words = ['awareness', 'education', 'prevention', 'help', 'support']
    exploitative_words = ['shocking', 'insane', 'crazy', 'unbelievable', 'clickbait']
    
    responsible_count = sum(1 for word in responsible_words if word in all_text['description'])
    exploitative_count = sum(1 for word in exploitative_words if word in all_text['title'])
    
    if responsible_count > exploitative_count:
        score += 0.3
    elif exploitative_count > responsible_count:
        score -= 0.4
    
    return max(min(score, 1.0), 0.0)

def calculate_educational_value(all_text):
    """Calculate educational value"""
    score = 0.3
    
    educational_words = ['learn', 'understand', 'awareness', 'important', 'education']
    matches = sum(1 for word in educational_words if word in all_text['description'])
    
    if matches > 0:
        score += 0.4
    
    return min(score, 1.0)

def calculate_confidence(data, components):
    """Calculate analysis confidence"""
    confidence = 0.3
    
    if data['title'].strip():
        confidence += 0.15
    if len(data['comments']) > 10:
        confidence += 0.25
    if data['viewCount'] > 1000:
        confidence += 0.15
    if data['transcript']['available']:
        confidence += 0.15
    
    return min(confidence, 1.0)

def get_score_color(score):
    """Get score color emoji"""
    if score >= 8:
        return "🟢"
    elif score >= 6:
        return "🟡"
    elif score >= 4:
        return "🟠"
    else:
        return "🔴"

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🎯 Specialized Content Analyzer</h1>
        <p>Advanced Analysis for Heartwarming, Motivational & Traumatic Content</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Category selection
    st.subheader("📋 Select Content Category")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("❤️ Heartwarming", use_container_width=True):
            st.session_state.selected_category = 'heartwarming_content'
    
    with col2:
        if st.button("💪 Motivational", use_container_width=True):
            st.session_state.selected_category = 'motivational_content'
    
    with col3:
        if st.button("⚠️ Traumatic Events", use_container_width=True):
            st.session_state.selected_category = 'traumatic_events'
    
    # Show selected category
    selected_category = st.session_state.selected_category
    category_info = CATEGORIES[selected_category]
    
    st.info(f"**Selected:** {category_info['emoji']} {category_info['name']} - {category_info['description']}")
    
    # Configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        api_key = st.text_input(
            "YouTube Data API v3 Key",
            type="password"
        )
        
        if not api_key:
            st.warning("🔑 API key required")
        
        st.markdown("---")
        st.write(f"**Current Category:** {category_info['emoji']} {category_info['name']}")
    
    # Main analysis
    st.subheader("🎬 Video Analysis")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        video_url = st.text_input(
            "🎥 YouTube Video URL:",
            placeholder="https://youtube.com/watch?v=example"
        )
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        analyze_button = st.button("🚀 Analyze", disabled=not api_key or not video_url, use_container_width=True)
    
    if analyze_button and video_url:
        video_id = extract_video_id(video_url)
        
        if not video_id:
            st.error("❌ Invalid YouTube URL")
        else:
            try:
                # Progress
                progress_bar = st.progress(0)
                progress_text = st.empty()
                
                progress_text.text("🔍 Fetching video data...")
                progress_bar.progress(30)
                
                # Fetch data
                video_data = fetch_youtube_data(video_id, api_key)
                
                progress_text.text("🧠 Running category analysis...")
                progress_bar.progress(70)
                
                # Analyze
                result = analyze_category_content(video_data, selected_category)
                
                progress_bar.progress(100)
                progress_text.text("✅ Analysis complete!")
                time.sleep(0.5)
                progress_text.empty()
                progress_bar.empty()
                
                # Results
                st.success("🎉 Analysis Complete!")
                
                # Main layout
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"### 📺 {video_data['title']}")
                    st.markdown(f"**Channel:** {video_data['channelTitle']}")
                    st.markdown(f"**Duration:** {video_data['duration']}")
                    
                    # Stats
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("👀 Views", f"{video_data['viewCount']:,}")
                    with col_b:
                        st.metric("👍 Likes", f"{video_data['likeCount']:,}")
                    with col_c:
                        st.metric("💬 Comments", f"{video_data['commentCount']:,}")
                
                with col2:
                    # Score
                    score = result['final_score']
                    confidence = result['confidence']
                    score_emoji = get_score_color(score)
                    
                    st.markdown(f"""
                    <div class="score-card">
                        <h2>{category_info['emoji']} Score</h2>
                        <h1 style="font-size: 3.5rem; margin: 0;">{score:.1f}</h1>
                        <h3>/10</h3>
                        <p>Confidence: {confidence:.0%}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Authenticity
                authenticity = result['authenticity']
                if authenticity == 'authentic':
                    st.success("✅ **AUTHENTIC CONTENT**")
                elif authenticity == 'questionable':
                    st.warning("⚠️ **QUESTIONABLE AUTHENTICITY**")
                elif authenticity == 'likely_staged':
                    st.error("❌ **LIKELY STAGED**")
                elif authenticity == 'responsible':
                    st.success("✅ **RESPONSIBLY PRESENTED**")
                elif authenticity == 'exploitative':
                    st.error("❌ **EXPLOITATIVE CONTENT**")
                
                # Component scores
                st.subheader("📊 Component Analysis")
                
                components = result['component_scores']
                
                for key, value in components.items():
                    component_score = value * 10
                    color_emoji = get_score_color(component_score)
                    
                    st.markdown(f"""
                    <div class="component-card">
                        <h4>{key.replace('_', ' ').title()}</h4>
                        <h3>{color_emoji} {component_score:.1f}/10</h3>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Timestamped moments
                moments = result['moments']
                if moments:
                    st.subheader("⏰ Key Moments")
                    
                    for moment in moments[:5]:
                        quality_emoji = "🌟" if moment['relevance_score'] >= 5.0 else "⭐"
                        
                        st.markdown(f"""
                        <div class="moment-highlight">
                            <strong>⏰ {moment['timestamp']}</strong> {quality_emoji}<br>
                            <em>"{moment['comment'][:120]}..."</em><br>
                            <small>Relevance: {moment['relevance_score']:.1f}</small>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    if len(moments) > 5:
                        st.info(f"💡 {len(moments) - 5} more moments found")
                
                # Assessment
                st.subheader("🎯 Assessment")
                
                if score >= 8.5:
                    st.success("🌟 **EXCELLENT** - Outstanding example of this category")
                elif score >= 7.0:
                    st.success("✅ **GOOD** - Strong category match")
                elif score >= 5.5:
                    st.info("⚠️ **MODERATE** - Some category elements")
                elif score >= 3.5:
                    st.warning("🟠 **WEAK** - Limited alignment")
                else:
                    st.error("❌ **POOR** - Does not fit category")
                
                # Transcript info
                if video_data['transcript']['available']:
                    st.info("✅ Transcript data was included in analysis")
                else:
                    st.warning("⚠️ No transcript available - analysis based on metadata only")
                
                # Save analysis
                if st.button("💾 Save Analysis"):
                    analysis_summary = {
                        'timestamp': datetime.now().isoformat(),
                        'video_id': video_id,
                        'title': video_data['title'],
                        'category': selected_category,
                        'score': score,
                        'confidence': confidence,
                        'authenticity': authenticity,
                        'moments': len(moments)
                    }
                    st.session_state.analysis_history.append(analysis_summary)
                    st.success("✅ Saved!")
                
                st.markdown(f"[🎥 **Watch Video**]({video_url})")
                
            except Exception as e:
                st.error(f"❌ Analysis failed: {str(e)}")
                if "403" in str(e):
                    st.info("💡 Check your API key")
                elif "429" in str(e):
                    st.info("💡 Rate limit exceeded")
    
    # History
    if st.session_state.analysis_history:
        st.markdown("---")
        st.header("📚 Analysis History")
        
        df = pd.DataFrame([
            {
                'Title': a['title'][:30] + '...' if len(a['title']) > 30 else a['title'],
                'Category': CATEGORIES[a['category']]['emoji'] + ' ' + CATEGORIES[a['category']]['name'][:8],
                'Score': f"{a['score']:.1f}",
                'Auth': a['authenticity'][:8],
                'Moments': a['moments'],
                'Date': datetime.fromisoformat(a['timestamp']).strftime('%m/%d')
            }
            for a in reversed(st.session_state.analysis_history[-10:])
        ])
        
        st.dataframe(df, use_container_width=True)
        
        if st.button("🗑️ Clear History"):
            st.session_state.analysis_history = []
            st.rerun()
    
    # Category baselines
    st.markdown("---")
    st.subheader("📊 Category Baselines")
    
    tab1, tab2, tab3 = st.tabs(["❤️ Heartwarming", "💪 Motivational", "⚠️ Traumatic"])
    
    with tab1:
        st.markdown("""
        **🌟 Excellent (8.5-10):** Genuine reunions, authentic emotional moments
        **✅ Good (7.0-8.4):** Sweet family content, real acts of kindness
        **⚠️ Moderate (5.5-6.9):** Mildly positive, questionable authenticity
        **❌ Poor (0-5.4):** Staged content, fake emotions
        """)
    
    with tab2:
        st.markdown("""
        **🌟 Excellent (8.5-10):** Documented transformations, real adversity overcome
        **✅ Good (7.0-8.4):** Authentic achievements, clear struggle narrative
        **⚠️ Moderate (5.5-6.9):** Some motivational elements, limited authenticity
        **❌ Poor (0-5.4):** Fake guru content, toxic positivity
        """)
    
    with tab3:
        st.markdown("""
        **🌟 Excellent (8.5-10):** Responsible news coverage, educational trauma content
        **✅ Good (7.0-8.4):** Serious events with appropriate context
        **⚠️ Moderate (5.5-6.9):** Somewhat serious, questionable presentation
        **❌ Poor (0-5.4):** Exploitative clickbait, sensationalized tragedy
        """)

if __name__ == "__main__":
main()
  

