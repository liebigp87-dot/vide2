import streamlit as st
import requests
import json
import re
import pandas as pd
from datetime import datetime
import time
import io

# Page configuration
st.set_page_config(
    page_title="AI Video Content Analyzer",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
        margin-bottom: 2rem;
    }
    .score-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        margin: 1rem 0;
    }
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 0.5rem 0;
    }
    .timestamp-moment {
        background: #e3f2fd;
        padding: 0.8rem;
        border-radius: 6px;
        border-left: 3px solid #2196f3;
        margin: 0.5rem 0;
    }
    .stButton > button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'analysis_history' not in st.session_state:
    st.session_state.analysis_history = []

# Category presets
CATEGORY_PRESETS = {
    'heartwarming moments': {
        'description': 'Content with specific emotional moments suitable for editing into clips',
        'keywords': ['touching', 'inspiring', 'reunion', 'kindness', 'helping others', 'surprise', 'generosity'],
        'emotional_indicators': ['cry', 'crying', 'tear', 'tears', 'emotional', 'touching', 'beautiful', 'sweet', 'love', 'happy', 'joy', 'smile', 'heart', 'feels']
    },
    'emotional disaster': {
        'description': 'Crisis content with specific dramatic moments suitable for clipping',
        'keywords': ['crisis', 'tragedy', 'shocking', 'devastating', 'breaking news', 'emergency', 'disaster'],
        'emotional_indicators': ['shock', 'devastating', 'tragic', 'heartbreaking', 'terrible', 'awful', 'scary', 'intense', 'dramatic']
    },
    'educational content': {
        'description': 'Educational videos with specific teachable moments for clipping',
        'keywords': ['tutorial', 'explanation', 'how-to', 'learning', 'educational', 'science', 'facts'],
        'emotional_indicators': ['learned', 'understand', 'explains', 'helpful', 'informative', 'knowledge']
    },
    'comedy/entertainment': {
        'description': 'Funny content with specific comedic moments for clipping',
        'keywords': ['funny', 'hilarious', 'comedy', 'entertaining', 'viral', 'meme', 'reaction'],
        'emotional_indicators': ['laugh', 'funny', 'hilarious', 'lol', 'died', 'killed me', 'comedy', 'joke']
    },
    'motivational/inspirational': {
        'description': 'Motivational content with specific inspiring moments for clipping',
        'keywords': ['motivation', 'inspiration', 'success', 'achievement', 'overcoming', 'goals', 'transformation'],
        'emotional_indicators': ['inspiring', 'motivated', 'amazing', 'incredible', 'wow', 'powerful', 'moved']
    }
}

# Weight configuration
CUSTOM_WEIGHTS = {
    'engagement_score': 0.05,
    'semantic_relevance': 0.45,
    'emotional_indicators': 0.35,
    'virality_potential': 0.1,
    'technical_quality': 0.05
}

def extract_video_id(url):
    """Extract YouTube video ID from URL"""
    pattern = r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)'
    match = re.search(pattern, url)
    return match.group(1) if match else None

def parse_duration(duration_str):
    """Parse YouTube duration format PT4M13S to readable format"""
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

@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_youtube_data(video_id, api_key):
    """Fetch YouTube video data using API"""
    try:
        # Fetch video details
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
            raise Exception("Video not found or is private/unavailable")
        
        video = video_data['items'][0]
        
        # Fetch comments
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
                comments = [
                    item['snippet']['topLevelComment']['snippet']['textDisplay']
                    for item in comments_data.get('items', [])
                ]
        except Exception as e:
            st.warning(f"Could not fetch comments: {str(e)}")
        
        # Parse and return data
        stats = video['statistics']
        snippet = video['snippet']
        content_details = video['contentDetails']
        
        return {
            'videoId': video_id,
            'title': snippet['title'],
            'description': snippet.get('description', ''),
            'viewCount': int(stats.get('viewCount', 0)),
            'likeCount': int(stats.get('likeCount', 0)),
            'commentCount': int(stats.get('commentCount', 0)),
            'tags': snippet.get('tags', []),
            'comments': comments,
            'duration': parse_duration(content_details['duration']),
            'publishedAt': snippet['publishedAt'],
            'channelTitle': snippet['channelTitle'],
            'thumbnails': snippet.get('thumbnails', {}),
            'raw_duration': content_details['duration']
        }
        
    except requests.exceptions.RequestException as e:
        if e.response and e.response.status_code == 403:
            raise Exception("API key error: Please check your YouTube API key and ensure YouTube Data API v3 is enabled")
        elif e.response and e.response.status_code == 429:
            raise Exception("API quota exceeded. Please try again later")
        else:
            raise Exception(f"Error fetching video data: {str(e)}")

def analyze_engagement_score(data):
    """Analyze engagement metrics"""
    if data['viewCount'] == 0:
        return 0
    
    like_ratio = data['likeCount'] / data['viewCount']
    comment_ratio = data['commentCount'] / data['viewCount']
    
    score = 0
    
    # Like ratio scoring
    if like_ratio > 0.05:
        score += 3
    elif like_ratio > 0.03:
        score += 2.5
    elif like_ratio > 0.01:
        score += 2
    elif like_ratio > 0.005:
        score += 1
    
    # Comment engagement
    if comment_ratio > 0.01:
        score += 2.5
    elif comment_ratio > 0.005:
        score += 2
    elif comment_ratio > 0.002:
        score += 1.5
    elif comment_ratio > 0.001:
        score += 1
    
    # View velocity (simplified)
    days_since_published = (datetime.now() - datetime.fromisoformat(data['publishedAt'].replace('Z', '+00:00'))).days
    if days_since_published > 0:
        views_per_day = data['viewCount'] / days_since_published
        if views_per_day > 10000:
            score += 2.5
        elif views_per_day > 5000:
            score += 2
        elif views_per_day > 1000:
            score += 1.5
        elif views_per_day > 100:
            score += 1
    
    return min(score, 10)

def extract_timestamped_moments(comments, category):
    """Extract timestamped moments from comments"""
    timestamp_pattern = r'(?:at\s+)?(\d{1,2}):(\d{2})|(\d{1,2}):(\d{2})|(\d+:\d+)'
    moments = []
    
    emotional_indicators = CATEGORY_PRESETS[category]['emotional_indicators']
    
    for i, comment in enumerate(comments):
        comment_lower = comment.lower()
        timestamps = re.findall(timestamp_pattern, comment_lower)
        
        if timestamps:
            has_emotional_context = any(indicator in comment_lower for indicator in emotional_indicators)
            
            if has_emotional_context:
                # Calculate relevance score
                relevance_score = sum(1 for indicator in emotional_indicators if indicator in comment_lower)
                if any(word in comment_lower for word in ['crying', 'bawling', 'sobbing', 'tears']):
                    relevance_score += 0.5
                
                for timestamp_match in timestamps:
                    timestamp = ':'.join(filter(None, timestamp_match))
                    moments.append({
                        'timestamp': timestamp,
                        'comment': comment,
                        'relevance_score': relevance_score,
                        'emotional_context': True
                    })
    
    return sorted(moments, key=lambda x: x['relevance_score'], reverse=True)

def analyze_semantic_relevance(data, category):
    """Analyze semantic relevance to category"""
    preset = CATEGORY_PRESETS[category]
    keywords = preset['keywords']
    
    # Combine text for analysis
    text_content = f"{data['title']} {data['description']} {' '.join(data['tags'])}".lower()
    
    # Keyword matching
    keyword_score = 0
    matched_keywords = []
    for keyword in keywords:
        if keyword.lower() in text_content:
            keyword_score += 2
            matched_keywords.append(keyword)
    
    # Extract timestamped moments
    timestamped_moments = extract_timestamped_moments(data['comments'], category)
    
    # Content quality scoring
    content_quality_score = 5.0
    
    # Title analysis
    title_lower = data['title'].lower()
    title_indicators = {
        'reaction': 1.5, 'surprise': 1.5, 'emotional': 1.0, 'touching': 1.0,
        'heartwarming': 1.5, 'mom': 1.0, 'dad': 1.0, 'family': 1.0,
        'cry': 1.2, 'tears': 1.2, 'beautiful': 0.8, 'amazing': 0.8
    }
    
    for indicator, value in title_indicators.items():
        if indicator in title_lower:
            content_quality_score += value
    
    # Timestamp bonus
    timestamp_bonus = min(len(timestamped_moments) * 1.2, 4.0)
    
    # Calculate final score
    base_score = (keyword_score + content_quality_score + timestamp_bonus) / 1.8
    final_score = min(base_score, 10)
    
    return {
        'score': final_score,
        'keyword_matches': len(matched_keywords),
        'matched_keywords': matched_keywords,
        'timestamped_moments': timestamped_moments,
        'moment_count': len(timestamped_moments),
        'timestamp_bonus': timestamp_bonus
    }

def analyze_emotional_indicators(data, timestamped_moments):
    """Analyze emotional indicators in comments"""
    if not data['comments']:
        return {
            'score': 5.0,
            'sentiment_score': 0,
            'timestamp_comments': 0,
            'analysis': 'No comments available for emotional analysis',
            'comment_breakdown': []
        }
    
    positive_words = ['love', 'beautiful', 'amazing', 'wonderful', 'touching', 'heartwarming', 
                     'cry', 'crying', 'tears', 'joy', 'happy', 'smile', 'moved', 'emotional', 'feels']
    intensity_words = ['crying', 'bawling', 'sobbing', 'tears', 'chills', 'goosebumps']
    negative_words = ['bad', 'terrible', 'awful', 'hate', 'boring', 'fake', 'staged', 'cringe']
    
    sentiment_score = 0
    timestamp_sentiment_bonus = 0
    comment_breakdown = []
    
    timestamp_pattern = r'(?:at\s+)?(\d{1,2}):(\d{2})|(\d{1,2}):(\d{2})|(\d+:\d+)'
    
    for comment in data['comments']:
        comment_lower = comment.lower()
        comment_score = 0
        found_words = []
        
        is_timestamped = bool(re.search(timestamp_pattern, comment_lower))
        
        # Positive words
        for word in positive_words:
            if word in comment_lower:
                comment_score += 0.5
                found_words.append(word)
                
                if is_timestamped and word in ['cry', 'crying', 'tears', 'emotional', 'touching', 'moved']:
                    timestamp_sentiment_bonus += 2.0
        
        # Intensity words
        for word in intensity_words:
            if word in comment_lower:
                comment_score += 1.0
                found_words.append(f"{word} (intensity)")
                
                if is_timestamped:
                    timestamp_sentiment_bonus += 3.0
        
        # Negative words
        for word in negative_words:
            if word in comment_lower:
                comment_score -= 0.3
                found_words.append(f"{word} (negative)")
        
        sentiment_score += comment_score
        
        if comment_score > 0.5 or is_timestamped or found_words:
            contribution = 'high' if comment_score > 1 else 'medium' if comment_score > 0.3 else 'low'
            comment_breakdown.append({
                'comment': comment,
                'score': comment_score,
                'is_timestamped': is_timestamped,
                'found_words': found_words,
                'contribution': contribution
            })
    
    # Calculate final score
    normalized_sentiment = min(sentiment_score / len(data['comments']) * 10, 10)
    moment_intensity_score = 5.0 + min(len(timestamped_moments) * 0.8, 3.0)
    
    final_score = min((normalized_sentiment + moment_intensity_score) / 2 + (timestamp_sentiment_bonus * 0.1), 10)
    
    return {
        'score': final_score,
        'sentiment_score': min(sentiment_score, 10),
        'timestamp_comments': len([c for c in data['comments'] if re.search(timestamp_pattern, c.lower())]),
        'timestamp_bonus': timestamp_sentiment_bonus,
        'analysis': f"{len(timestamped_moments)} timestamped moments found. {'EXCELLENT' if timestamp_sentiment_bonus > 5 else 'GOOD' if timestamp_sentiment_bonus > 2 else 'LIMITED'} emotional quality.",
        'comment_breakdown': sorted(comment_breakdown, key=lambda x: x['score'], reverse=True)[:10]
    }

def analyze_virality_potential(data):
    """Analyze virality potential"""
    if data['viewCount'] == 0:
        return {'score': 0, 'factors': []}
    
    viral_score = 5.0
    factors = []
    
    # Engagement rate
    engagement_rate = (data['likeCount'] + data['commentCount']) / data['viewCount']
    if engagement_rate > 0.05:
        viral_score += 2.0
        factors.append(f"High engagement rate: {(engagement_rate * 100):.3f}%")
    elif engagement_rate > 0.02:
        viral_score += 1.5
        factors.append(f"Good engagement rate: {(engagement_rate * 100):.3f}%")
    
    # Viral keywords
    viral_keywords = ['reaction', 'surprising', 'shocking', 'amazing', 'incredible', 'unbelievable', 'viral', 'trending']
    content_text = f"{data['title']} {data['description']}".lower()
    keyword_matches = sum(1 for keyword in viral_keywords if keyword in content_text)
    
    if keyword_matches > 0:
        viral_score += keyword_matches * 0.3
        factors.append(f"Viral keywords found: {keyword_matches}")
    
    # Duration factor
    duration_parts = data['duration'].split(':')
    if len(duration_parts) == 2:
        minutes = int(duration_parts[0])
        if minutes < 5:
            viral_score += 1.5
            factors.append("Good length for clips (under 5 minutes)")
        elif minutes < 10:
            viral_score += 1.0
            factors.append("Decent length for clips")
    
    return {
        'score': min(viral_score, 10),
        'factors': factors
    }

def analyze_technical_quality(data):
    """Analyze technical quality indicators"""
    quality_score = 6.5
    factors = []
    
    # View count as quality indicator
    if data['viewCount'] > 1000000:
        quality_score += 1.5
        factors.append("High view count indicates good quality")
    elif data['viewCount'] > 100000:
        quality_score += 1.0
        factors.append("Decent view count")
    
    # Title length
    title_length = len(data['title'])
    if 20 < title_length < 100:
        quality_score += 0.5
        factors.append("Good title length")
    
    # Description length
    description_length = len(data['description'])
    if description_length > 100:
        quality_score += 0.5
        factors.append("Detailed description")
    
    return {
        'score': min(quality_score, 10),
        'factors': factors
    }

def calculate_overall_score(ratings):
    """Calculate weighted overall score"""
    return sum(ratings[key] * CUSTOM_WEIGHTS[key] for key in ratings)

def get_score_color(score):
    """Get color based on score"""
    if score >= 8:
        return "🟢"
    elif score >= 6:
        return "🟡"
    else:
        return "🔴"

# Main Streamlit App
def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🎬 AI Video Content Analyzer</h1>
        <p>Analyze YouTube videos for editing suitability using real API data</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # API Key input
        api_key = st.text_input(
            "YouTube Data API v3 Key",
            type="password",
            help="Get your API key from Google Cloud Console"
        )
        
        if not api_key:
            st.warning("Please enter your YouTube API key to analyze real videos")
            st.info("Get your API key at: https://console.developers.google.com/")
        
        # Category selection
        st.subheader("📋 Content Category")
        selected_category = st.selectbox(
            "Choose category",
            options=list(CATEGORY_PRESETS.keys()),
            format_func=lambda x: x.replace('_', ' ').title()
        )
        
        # Custom category
        custom_category = st.text_input("Or enter custom category:")
        category = custom_category if custom_category else selected_category
        
        # Category description
        if not custom_category:
            st.info(CATEGORY_PRESETS[selected_category]['description'])
        
        # Bulk analysis mode
        st.subheader("📊 Analysis Mode")
        bulk_mode = st.checkbox("Bulk Analysis Mode")
    
    # Main content area
    if bulk_mode:
        st.header("📊 Bulk Video Analysis")
        
        bulk_urls = st.text_area(
            "Enter YouTube URLs (one per line):",
            height=150,
            placeholder="https://youtube.com/watch?v=example1\nhttps://youtube.com/watch?v=example2"
        )
        
        if st.button("🚀 Analyze All Videos", disabled=not api_key):
            if bulk_urls.strip():
                urls = [url.strip() for url in bulk_urls.split('\n') if url.strip()]
                
                if urls:
                    progress_bar = st.progress(0)
                    results_container = st.container()
                    bulk_results = []
                    
                    for i, url in enumerate(urls):
                        try:
                            video_id = extract_video_id(url)
                            if not video_id:
                                st.error(f"Invalid URL: {url}")
                                continue
                            
                            # Fetch and analyze
                            with st.spinner(f"Analyzing video {i+1}/{len(urls)}..."):
                                youtube_data = fetch_youtube_data(video_id, api_key)
                                
                                # Run all analyses
                                engagement_score = analyze_engagement_score(youtube_data)
                                semantic_analysis = analyze_semantic_relevance(youtube_data, category)
                                emotional_analysis = analyze_emotional_indicators(youtube_data, semantic_analysis['timestamped_moments'])
                                virality_analysis = analyze_virality_potential(youtube_data)
                                technical_analysis = analyze_technical_quality(youtube_data)
                                
                                ratings = {
                                    'engagement_score': engagement_score,
                                    'semantic_relevance': semantic_analysis['score'],
                                    'emotional_indicators': emotional_analysis['score'],
                                    'virality_potential': virality_analysis['score'],
                                    'technical_quality': technical_analysis['score']
                                }
                                
                                overall_score = calculate_overall_score(ratings)
                                suitability = 'HIGH' if overall_score >= 7 else 'MODERATE' if overall_score >= 5 else 'LOW'
                                
                                result = {
                                    'title': youtube_data['title'],
                                    'video_id': video_id,
                                    'url': url,
                                    'overall_score': overall_score,
                                    'suitability': suitability,
                                    'timestamped_moments': len(semantic_analysis['timestamped_moments']),
                                    'view_count': youtube_data['viewCount'],
                                    'like_count': youtube_data['likeCount'],
                                    'comment_count': youtube_data['commentCount'],
                                    'ratings': ratings
                                }
                                
                                bulk_results.append(result)
                                progress_bar.progress((i + 1) / len(urls))
                                
                        except Exception as e:
                            st.error(f"Error analyzing {url}: {str(e)}")
                            continue
                    
                    # Display bulk results
                    if bulk_results:
                        st.success(f"✅ Analyzed {len(bulk_results)} videos successfully!")
                        
                        # Summary metrics
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            high_count = sum(1 for r in bulk_results if r['suitability'] == 'HIGH')
                            st.metric("🟢 High Suitability", high_count)
                        with col2:
                            moderate_count = sum(1 for r in bulk_results if r['suitability'] == 'MODERATE')
                            st.metric("🟡 Moderate Suitability", moderate_count)
                        with col3:
                            low_count = sum(1 for r in bulk_results if r['suitability'] == 'LOW')
                            st.metric("🔴 Low Suitability", low_count)
                        
                        # Results table
                        df = pd.DataFrame([
                            {
                                'Title': r['title'][:50] + '...' if len(r['title']) > 50 else r['title'],
                                'Overall Score': f"{r['overall_score']:.1f}/10",
                                'Suitability': r['suitability'],
                                'Timestamped Moments': r['timestamped_moments'],
                                'Views': f"{r['view_count']:,}",
                                'Likes': f"{r['like_count']:,}",
                                'Video ID': r['video_id']
                            }
                            for r in bulk_results
                        ])
                        
                        st.dataframe(df, use_container_width=True)
                        
                        # Export functionality
                        if st.button("💾 Export Results"):
                            export_data = {
                                'analysis_date': datetime.now().isoformat(),
                                'category': category,
                                'total_videos': len(bulk_results),
                                'results': bulk_results
                            }
                            
                            json_str = json.dumps(export_data, indent=2)
                            st.download_button(
                                label="📄 Download JSON",
                                data=json_str,
                                file_name=f"bulk_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                                mime="application/json"
                            )
            else:
                st.warning("Please enter at least one video URL")
    
    else:
        # Single video analysis
        st.header("🎯 Single Video Analysis")
        
        video_url = st.text_input(
            "YouTube Video URL:",
            placeholder="https://youtube.com/watch?v=example"
        )
        
        if st.button("🔍 Analyze Video", disabled=not api_key or not video_url):
            if video_url:
                video_id = extract_video_id(video_url)
                
                if not video_id:
                    st.error("❌ Invalid YouTube URL. Please check the format.")
                else:
                    try:
                        # Progress indicator
                        progress_text = st.empty()
                        progress_bar = st.progress(0)
                        
                        progress_text.text("📡 Fetching video data...")
                        progress_bar.progress(20)
                        
                        # Fetch YouTube data
                        youtube_data = fetch_youtube_data(video_id, api_key)
                        
                        progress_text.text("🧠 Running AI analysis...")
                        progress_bar.progress(60)
                        
                        # Run analyses
                        engagement_score = analyze_engagement_score(youtube_data)
                        semantic_analysis = analyze_semantic_relevance(youtube_data, category)
                        emotional_analysis = analyze_emotional_indicators(youtube_data, semantic_analysis['timestamped_moments'])
                        virality_analysis = analyze_virality_potential(youtube_data)
                        technical_analysis = analyze_technical_quality(youtube_data)
                        
                        progress_text.text("📊 Calculating results...")
                        progress_bar.progress(80)
                        
                        # Calculate overall score
                        ratings = {
                            'engagement_score': engagement_score,
                            'semantic_relevance': semantic_analysis['score'],
                            'emotional_indicators': emotional_analysis['score'],
                            'virality_potential': virality_analysis['score'],
                            'technical_quality': technical_analysis['score']
                        }
                        
                        overall_score = calculate_overall_score(ratings)
                        
                        progress_bar.progress(100)
                        progress_text.text("✅ Analysis complete!")
                        time.sleep(0.5)
                        progress_text.empty()
                        progress_bar.empty()
                        
                        # Display results
                        st.success("🎉 Analysis Complete!")
                        
                        # Video info header
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.markdown(f"### 📺 {youtube_data['title']}")
                            st.markdown(f"**Channel:** {youtube_data['channelTitle']}")
                            st.markdown(f"**Category:** {category}")
                            
                            # Basic stats
                            col_a, col_b, col_c = st.columns(3)
                            with col_a:
                                st.metric("👀 Views", f"{youtube_data['viewCount']:,}")
                            with col_b:
                                st.metric("👍 Likes", f"{youtube_data['likeCount']:,}")
                            with col_c:
                                st.metric("💬 Comments", f"{youtube_data['commentCount']:,}")
                        
                        with col2:
                            # Overall score card
                            score_emoji = get_score_color(overall_score)
                            st.markdown(f"""
                            <div class="score-card">
                                <h2>{score_emoji} Overall Score</h2>
                                <h1 style="margin: 0;">{overall_score:.1f}/10</h1>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        # Detailed scores
                        st.subheader("📊 Detailed Analysis")
                        
                        score_cols = st.columns(5)
                        score_names = ['Engagement', 'Content Match', 'Moment Quality', 'Clip Potential', 'Technical']
                        score_keys = list(ratings.keys())
                        
                        for i, (col, name, key) in enumerate(zip(score_cols, score_names, score_keys)):
                            with col:
                                score = ratings[key]
                                color_emoji = get_score_color(score)
                                st.markdown(f"""
                                <div class="metric-card">
                                    <h4>{color_emoji} {name}</h4>
                                    <h3>{score:.1f}/10</h3>
                                    <small>{int(CUSTOM_WEIGHTS[key] * 100)}% weight</small>
                                </div>
                                """, unsafe_allow_html=True)
                        
                        # Analysis details
                        st.subheader("🔍 Analysis Details")
                        
                        # Content Analysis
                        with st.expander("📝 Content Analysis", expanded=True):
                            st.write(f"**Score:** {semantic_analysis['score']:.1f}/10")
                            st.write(f"**Keyword matches:** {semantic_analysis['keyword_matches']}")
                            if semantic_analysis['matched_keywords']:
                                st.write(f"**Matched keywords:** {', '.join(semantic_analysis['matched_keywords'])}")
                            st.write(f"**Timestamped moments found:** {semantic_analysis['moment_count']} 🎯")
                            
                            # Show timestamped moments
                            if semantic_analysis['timestamped_moments']:
                                st.write("**🎬 Timestamped Moments (perfect for editing):**")
                                for moment in semantic_analysis['timestamped_moments'][:5]:
                                    st.markdown(f"""
                                    <div class="timestamp-moment">
                                        <strong>⏰ {moment['timestamp']}</strong> (Score: {moment['relevance_score']:.1f})<br>
                                        <em>"{moment['comment'][:100]}..."</em>
                                    </div>
                                    """, unsafe_allow_html=True)
                                
                                if len(semantic_analysis['timestamped_moments']) > 5:
                                    st.write(f"*And {len(semantic_analysis['timestamped_moments']) - 5} more timestamped moments...*")
                        
                        # Emotional Analysis
                        with st.expander("❤️ Emotional Analysis"):
                            st.write(f"**Score:** {emotional_analysis['score']:.1f}/10")
                            st.write(f"**Analysis:** {emotional_analysis['analysis']}")
                            st.write(f"**Timestamped comments:** {emotional_analysis['timestamp_comments']}")
                            st.write(f"**Sentiment score:** {emotional_analysis['sentiment_score']:.1f}/10")
                            
                            if emotional_analysis['comment_breakdown']:
                                st.write("**📝 Top Comments Influencing Score:**")
                                for comment_data in emotional_analysis['comment_breakdown'][:3]:
                                    contribution_color = "🟢" if comment_data['contribution'] == 'high' else "🟡" if comment_data['contribution'] == 'medium' else "🔴"
                                    st.markdown(f"""
                                    **{contribution_color} Score: +{comment_data['score']:.1f}** {'⏰' if comment_data['is_timestamped'] else ''}  
                                    *"{comment_data['comment'][:80]}..."*  
                                    Words found: {', '.join(comment_data['found_words'][:3])}
                                    """)
                        
                        # Virality Analysis
                        with st.expander("🚀 Virality & Clip Potential"):
                            st.write(f"**Score:** {virality_analysis['score']:.1f}/10")
                            if virality_analysis['factors']:
                                st.write("**Factors:**")
                                for factor in virality_analysis['factors']:
                                    st.write(f"• {factor}")
                        
                        # Technical Analysis
                        with st.expander("⚙️ Technical Quality"):
                            st.write(f"**Score:** {technical_analysis['score']:.1f}/10")
                            if technical_analysis['factors']:
                                st.write("**Quality indicators:**")
                                for factor in technical_analysis['factors']:
                                    st.write(f"• {factor}")
                        
                        # Editing Suitability Summary
                        st.subheader("🎬 Editing Suitability Assessment")
                        
                        if overall_score >= 7:
                            st.success("✅ **HIGH SUITABILITY** - Video contains clear, identifiable moments perfect for clipping")
                        elif overall_score >= 5:
                            st.warning("⚠️ **MODERATE SUITABILITY** - Video has some suitable content but may require more careful selection")
                        else:
                            st.error("❌ **LOW SUITABILITY** - Limited identifiable moments or poor content match")
                        
                        if semantic_analysis['timestamped_moments']:
                            st.info(f"🎯 **{len(semantic_analysis['timestamped_moments'])} specific moments identified by viewers with timestamps - excellent for editing!**")
                        
                        # Save analysis
                        analysis_result = {
                            'timestamp': datetime.now().isoformat(),
                            'video_id': video_id,
                            'video_data': youtube_data,
                            'category': category,
                            'ratings': ratings,
                            'overall_score': overall_score,
                            'timestamped_moments': len(semantic_analysis['timestamped_moments']),
                            'suitability': 'HIGH' if overall_score >= 7 else 'MODERATE' if overall_score >= 5 else 'LOW'
                        }
                        
                        if st.button("💾 Save Analysis"):
                            st.session_state.analysis_history.append(analysis_result)
                            st.success("Analysis saved to history!")
                        
                        # Export single analysis
                        if st.button("📄 Export Analysis"):
                            json_str = json.dumps(analysis_result, indent=2, default=str)
                            st.download_button(
                                label="💾 Download JSON",
                                data=json_str,
                                file_name=f"video_analysis_{video_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                                mime="application/json"
                            )
                        
                        # Watch video link
                        st.markdown(f"[🎥 **Watch Video on YouTube**]({video_url})")
                        
                    except Exception as e:
                        progress_text.empty()
                        progress_bar.empty()
                        st.error(f"❌ Error analyzing video: {str(e)}")
                        
                        if "403" in str(e) or "API key" in str(e):
                            st.info("💡 Make sure your YouTube Data API v3 key is correct and the API is enabled in Google Cloud Console")
                        elif "429" in str(e) or "quota" in str(e):
                            st.info("💡 API quota exceeded. Try again later or check your quota limits in Google Cloud Console")
    
    # Analysis History Section
    if st.session_state.analysis_history:
        st.header("📚 Analysis History")
        
        # Summary stats
        total_analyses = len(st.session_state.analysis_history)
        avg_score = sum(a['overall_score'] for a in st.session_state.analysis_history) / total_analyses
        high_suitability = sum(1 for a in st.session_state.analysis_history if a['overall_score'] >= 7)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Analyses", total_analyses)
        with col2:
            st.metric("Average Score", f"{avg_score:.1f}/10")
        with col3:
            st.metric("High Suitability", high_suitability)
        
        # History table
        history_df = pd.DataFrame([
            {
                'Date': datetime.fromisoformat(a['timestamp']).strftime('%Y-%m-%d %H:%M'),
                'Title': a['video_data']['title'][:40] + '...' if len(a['video_data']['title']) > 40 else a['video_data']['title'],
                'Score': f"{a['overall_score']:.1f}/10",
                'Suitability': a['suitability'],
                'Moments': a['timestamped_moments'],
                'Views': f"{a['video_data']['viewCount']:,}",
                'Category': a['category']
            }
            for a in reversed(st.session_state.analysis_history[-10:])  # Show last 10
        ])
        
        st.dataframe(history_df, use_container_width=True)
        
        # Export history
        if st.button("📤 Export All History"):
            export_data = {
                'export_date': datetime.now().isoformat(),
                'total_analyses': len(st.session_state.analysis_history),
                'analyses': st.session_state.analysis_history
            }
            
            json_str = json.dumps(export_data, indent=2, default=str)
            st.download_button(
                label="💾 Download History JSON",
                data=json_str,
                file_name=f"analysis_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        
        # Clear history
        if st.button("🗑️ Clear History", type="secondary"):
            if st.checkbox("Confirm clear history"):
                st.session_state.analysis_history = []
                st.success("History cleared!")
                st.experimental_rerun()

if __name__ == "__main__":
    main()