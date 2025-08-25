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
import xml.etree.ElementTree as ET
from urllib.parse import unquote

# Page configuration
st.set_page_config(
    page_title="Advanced Content Analyzer",
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
    .category-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
    .score-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 15px;
        text-align: center;
        margin: 1rem 0;
        box-shadow: 0 4px 20px rgba(0,0,0,0.2);
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
        background: linear-gradient(135deg, #e8f5e8 0%, #f0f8f0 100%);
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #28a745;
        margin: 0.8rem 0;
        color: #155724;
    }
    .transcript-segment {
        background: #f8f9fa;
        padding: 0.8rem;
        border-radius: 6px;
        margin: 0.5rem 0;
        border-left: 3px solid #6c757d;
        font-family: monospace;
        font-size: 0.9em;
    }
    .authenticity-indicator {
        padding: 0.4rem 0.8rem;
        border-radius: 20px;
        margin: 0.2rem;
        display: inline-block;
        font-size: 0.85em;
        font-weight: bold;
    }
    .authentic { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
    .questionable { background: #fff3cd; color: #856404; border: 1px solid #ffeaa7; }
    .staged { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
</style>
""", unsafe_allow_html=True)

# Session state initialization
if 'analysis_history' not in st.session_state:
    st.session_state.analysis_history = []

# Specialized category definitions
SPECIALIZED_CATEGORIES = {
    'heartwarming_content': {
        'name': 'Heartwarming Content',
        'emoji': '❤️',
        'description': 'Genuine emotional moments that create positive feelings',
        'authenticity_signals': {
            'genuine': ['spontaneous', 'unexpected', 'real reaction', 'candid', 'unscripted', 'natural'],
            'staged_warnings': ['sponsored', 'ad', 'promotional', 'fake', 'acting', 'scripted', 'setup']
        },
        'content_types': {
            'reunions': ['reunion', 'homecoming', 'surprise visit', 'long distance', 'deployed', 'military'],
            'acts_of_kindness': ['helped', 'donated', 'volunteer', 'charity', 'generous', 'gave', 'sacrifice'],
            'life_events': ['proposal', 'wedding', 'birth', 'adoption', 'graduation', 'achievement'],
            'rescues': ['rescue', 'saved', 'found', 'lost pet', 'missing', 'search']
        },
        'viewer_emotions': {
            'strong': ['crying', 'sobbing', 'bawling', 'tears streaming', 'ugly crying', 'emotional wreck'],
            'moderate': ['tears', 'emotional', 'touched', 'moved', 'feels', 'heart melting'],
            'positive': ['happy tears', 'joy', 'beautiful', 'sweet', 'precious', 'wholesome', 'pure']
        },
        'speech_patterns': {
            'emotional_speech': ['voice cracking', 'choking up', 'speechless', 'overwhelmed'],
            'positive_words': ['thank you', 'grateful', 'blessed', 'amazing', 'incredible', 'beautiful'],
            'family_language': ['mom', 'dad', 'family', 'love you', 'missed you', 'proud of you']
        }
    },
    'motivational_content': {
        'name': 'Inspiring/Motivational Content',
        'emoji': '💪',
        'description': 'Content that genuinely inspires and motivates through real achievement',
        'authenticity_signals': {
            'genuine': ['documented journey', 'progress over time', 'struggle shown', 'setbacks mentioned'],
            'staged_warnings': ['overnight success', 'easy money', 'secret trick', 'one simple hack']
        },
        'content_types': {
            'transformation': ['lost weight', 'got fit', 'changed life', 'transformation', 'before after'],
            'overcoming_adversity': ['overcame', 'despite', 'against odds', 'disability', 'poverty', 'addiction'],
            'achievement': ['graduated', 'promotion', 'business success', 'competition won', 'record broken'],
            'perseverance': ['never gave up', 'kept trying', 'persistence', 'dedication', 'years of work']
        },
        'viewer_emotions': {
            'inspired': ['motivated', 'inspired', 'pumped up', 'ready to work', 'fired up'],
            'impressed': ['incredible', 'amazing', 'unbelievable', 'respect', 'legend', 'beast'],
            'relatable': ['needed this', 'perfect timing', 'exactly what I needed', 'motivation']
        },
        'speech_patterns': {
            'struggle_language': ['it was hard', 'difficult times', 'wanted to quit', 'almost gave up'],
            'breakthrough_language': ['turning point', 'everything changed', 'breakthrough moment'],
            'advice_language': ['key is', 'secret is', 'most important thing', 'advice', 'lesson learned']
        }
    },
    'traumatic_events': {
        'name': 'Traumatic Events',
        'emoji': '⚠️',
        'description': 'Serious events with significant emotional/psychological impact',
        'authenticity_signals': {
            'genuine': ['breaking news', 'live coverage', 'witness account', 'survivor story', 'documentary'],
            'staged_warnings': ['clickbait', 'dramatic music', 'sensationalized', 'views only', 'exploitative', 'shock value']
        },
        'content_types': {
            'natural_disasters': ['earthquake', 'hurricane', 'flood', 'wildfire', 'tsunami', 'tornado'],
            'accidents': ['crash', 'accident', 'collision', 'emergency', 'rescue operation'],
            'personal_trauma': ['loss', 'death', 'injury', 'diagnosis', 'tragedy', 'victim'],
            'social_events': ['protest', 'conflict', 'violence', 'crisis', 'emergency']
        },
        'viewer_emotions': {
            'shock': ['shocked', 'can\'t believe', 'unbelievable', 'devastating', 'horrific'],
            'empathy': ['prayers', 'thoughts and prayers', 'heart goes out', 'so sorry'],
            'concern': ['hope everyone ok', 'is everyone safe', 'any updates', 'what happened']
        },
        'speech_patterns': {
            'breaking_news': ['breaking news', 'just in', 'developing story', 'live coverage'],
            'witness_accounts': ['i saw', 'i was there', 'happened so fast', 'couldn\'t believe'],
            'official_statements': ['authorities confirm', 'police report', 'official statement']
        }
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

def get_video_transcript(video_id):
    """Attempt to get video transcript"""
    transcript_data = {
        'available': False,
        'text': '',
        'segments': [],
        'source': 'none'
    }
    
    try:
        caption_url = f"https://www.youtube.com/api/timedtext?lang=en&v={video_id}"
        response = requests.get(caption_url, timeout=10)
        
        if response.status_code == 200 and response.text:
            try:
                root = ET.fromstring(response.text)
                segments = []
                full_text = []
                
                for text_elem in root.findall('.//text'):
                    start_time = float(text_elem.get('start', 0))
                    duration = float(text_elem.get('dur', 0))
                    text_content = unquote(text_elem.text or '').strip()
                    
                    if text_content:
                        segments.append({
                            'start': start_time,
                            'duration': duration,
                            'text': text_content
                        })
                        full_text.append(text_content)
                
                if segments:
                    transcript_data.update({
                        'available': True,
                        'text': ' '.join(full_text),
                        'segments': segments,
                        'source': 'youtube_captions'
                    })
            except ET.ParseError:
                pass
    except Exception:
        pass
    
    return transcript_data

@st.cache_data(ttl=300)
def fetch_comprehensive_data(video_id, api_key):
    """Fetch all available data for comprehensive analysis"""
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
        
        # Enhanced comments
        comments_data = fetch_enhanced_comments(video_id, api_key)
        
        # Video transcript
        transcript_data = get_video_transcript(video_id)
        
        # Channel context
        channel_info = fetch_channel_info(snippet['channelId'], api_key)
        
        # Thumbnail analysis
        thumbnail_analysis = analyze_thumbnail(video_id)
        
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
            'channelId': snippet['channelId'],
            'comments': comments_data['comments'],
            'comment_sentiment': comments_data['sentiment_analysis'],
            'transcript': transcript_data,
            'channel_info': channel_info,
            'thumbnail_analysis': thumbnail_analysis,
            'tags': snippet.get('tags', [])
        }
        
    except requests.exceptions.RequestException as e:
        if e.response and e.response.status_code == 403:
            raise Exception("API key error: Check your YouTube Data API v3 key")
        elif e.response and e.response.status_code == 429:
            raise Exception("API quota exceeded. Try again later")
        else:
            raise Exception(f"Error fetching data: {str(e)}")

def fetch_enhanced_comments(video_id, api_key, max_results=150):
    """Fetch and analyze comments comprehensively"""
    comments = []
    sentiment_analysis = {
        'positive': 0, 'negative': 0, 'neutral': 0, 'total': 0,
        'emotional_intensity': 0, 'authenticity_score': 0
    }
    
    try:
        comments_url = f"https://www.googleapis.com/youtube/v3/commentThreads"
        
        for order_type in ['relevance', 'time']:
            comments_params = {
                'part': 'snippet',
                'videoId': video_id,
                'maxResults': 75,
                'order': order_type,
                'key': api_key
            }
            
            response = requests.get(comments_url, params=comments_params)
            if response.status_code == 200:
                data = response.json()
                
                for item in data.get('items', []):
                    comment_snippet = item['snippet']['topLevelComment']['snippet']
                    comment_text = comment_snippet['textDisplay']
                    like_count = comment_snippet.get('likeCount', 0)
                    
                    if comment_text not in comments:
                        comments.append(comment_text)
                        
                        sentiment = analyze_deep_sentiment(comment_text)
                        sentiment_analysis[sentiment] += 1
                        sentiment_analysis['total'] += 1
                        
                        if like_count > 10:
                            sentiment_analysis['emotional_intensity'] += like_count * 0.1
    
    except Exception as e:
        st.warning(f"Limited comment access: {str(e)}")
    
    return {
        'comments': comments,
        'sentiment_analysis': sentiment_analysis
    }

def fetch_channel_info(channel_id, api_key):
    """Get channel context"""
    try:
        channel_url = f"https://www.googleapis.com/youtube/v3/channels"
        params = {
            'part': 'snippet,statistics',
            'id': channel_id,
            'key': api_key
        }
        
        response = requests.get(channel_url, params=params)
        if response.status_code == 200:
            data = response.json()
            if data.get('items'):
                channel = data['items'][0]
                return {
                    'subscriber_count': int(channel['statistics'].get('subscriberCount', 0)),
                    'video_count': int(channel['statistics'].get('videoCount', 0)),
                    'description': channel['snippet'].get('description', ''),
                    'created_date': channel['snippet'].get('publishedAt', '')
                }
    except:
        pass
    
    return {'subscriber_count': 0, 'video_count': 0, 'description': '', 'created_date': ''}

def analyze_thumbnail(video_id):
    """Analyze video thumbnail for visual cues"""
    try:
        thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
        response = requests.get(thumbnail_url, timeout=10)
        
        if response.status_code == 200:
            image = Image.open(io.BytesIO(response.content))
            image_array = np.array(image)
            
            brightness = float(np.mean(image_array))
            contrast = float(np.std(image_array))
            
            red_avg = float(np.mean(image_array[:,:,0]))
            green_avg = float(np.mean(image_array[:,:,1]))
            blue_avg = float(np.mean(image_array[:,:,2]))
            
            return {
                'available': True,
                'brightness': brightness,
                'contrast': contrast,
                'color_profile': {
                    'red_dominant': red_avg > (green_avg + blue_avg) / 2 * 1.2,
                    'warm_tones': (red_avg + green_avg) > blue_avg * 1.3,
                    'cold_tones': blue_avg > (red_avg + green_avg) / 2 * 1.2
                },
                'visual_quality': min((brightness / 255 + contrast / 100) / 2, 1.0)
            }
    except:
        pass
    
    return {
        'available': False,
        'brightness': 128,
        'contrast': 40,
        'color_profile': {'red_dominant': False, 'warm_tones': False, 'cold_tones': False},
        'visual_quality': 0.5
    }

def analyze_deep_sentiment(comment_text):
    """Deep sentiment analysis for comments"""
    comment_lower = comment_text.lower()
    
    very_positive = ['amazing', 'incredible', 'beautiful', 'perfect', 'love', 'best', 'crying', 'tears', 'emotional', 'touching', 'moving']
    very_negative = ['terrible', 'awful', 'worst', 'hate', 'disgusting', 'fake', 'staged', 'cringe']
    positive_words = ['good', 'nice', 'great', 'cool', 'sweet', 'lovely', 'happy', 'joy', 'smile', 'fun']
    negative_words = ['bad', 'not good', 'boring', 'meh', 'okay', 'whatever', 'disappointed']
    
    very_pos_count = sum(1 for word in very_positive if word in comment_lower)
    very_neg_count = sum(1 for word in very_negative if word in comment_lower)
    pos_count = sum(1 for word in positive_words if word in comment_lower)
    neg_count = sum(1 for word in negative_words if word in comment_lower)
    
    total_positive = very_pos_count * 2 + pos_count
    total_negative = very_neg_count * 2 + neg_count
    
    if total_positive > total_negative:
        return 'positive'
    elif total_negative > total_positive:
        return 'negative'
    else:
        return 'neutral'

def extract_timestamped_moments(comments, category_key):
    """Extract timestamped moments with category-specific relevance"""
    timestamp_pattern = r'(?:at\s+)?(\d{1,2}):(\d{2})|(\d{1,2}):(\d{2})|(\d+:\d+)'
    moments = []
    
    category_data = SPECIALIZED_CATEGORIES[category_key]
    
    for comment in comments:
        comment_lower = comment.lower()
        timestamps = re.findall(timestamp_pattern, comment_lower)
        
        if timestamps:
            relevance_score = calculate_moment_relevance(comment_lower, category_data)
            
            if relevance_score > 0:
                for timestamp_match in timestamps:
                    timestamp = ':'.join(filter(None, timestamp_match))
                    moments.append({
                        'timestamp': timestamp,
                        'comment': comment,
                        'relevance_score': relevance_score,
                        'sentiment': analyze_deep_sentiment(comment),
                        'category_indicators': get_category_indicators(comment_lower, category_data)
                    })
    
    return sorted(moments, key=lambda x: x['relevance_score'], reverse=True)

def calculate_moment_relevance(comment_lower, category_data):
    """Calculate how relevant a timestamped moment is to the category"""
    score = 0
    
    for content_type, keywords in category_data['content_types'].items():
        matches = sum(1 for kw in keywords if kw in comment_lower)
        if matches > 0:
            score += matches * 2.0
    
    for emotion_level, words in category_data['viewer_emotions'].items():
        matches = sum(1 for word in words if word in comment_lower)
        if emotion_level == 'strong':
            score += matches * 3.0
        elif emotion_level == 'moderate':
            score += matches * 2.0
        else:
            score += matches * 1.0
    
    context_words = ['this part', 'here', 'moment', 'scene', 'exactly', 'perfect', 'best part', 'favorite']
    context_matches = sum(1 for word in context_words if word in comment_lower)
    score += context_matches * 1.5
    
    return score

def get_category_indicators(comment_lower, category_data):
    """Get specific indicators found in comment"""
    indicators = {
        'content_types': [],
        'emotions': [],
        'authenticity': 'unknown'
    }
    
    for content_type, keywords in category_data['content_types'].items():
        matches = [kw for kw in keywords if kw in comment_lower]
        if matches:
            indicators['content_types'].append(content_type)
    
    for emotion_level, words in category_data['viewer_emotions'].items():
        matches = [word for word in words if word in comment_lower]
        if matches:
            indicators['emotions'].extend(matches[:3])
    
    genuine_signals = category_data['authenticity_signals']['genuine']
    staged_warnings = category_data['authenticity_signals']['staged_warnings']
    
    if any(signal in comment_lower for signal in genuine_signals):
        indicators['authenticity'] = 'genuine'
    elif any(warning in comment_lower for warning in staged_warnings):
        indicators['authenticity'] = 'questionable'
    
    return indicators

# Analysis functions
def assess_authenticity(all_text, category_data, content_type):
    """Assess content authenticity"""
    score = 0.5
    
    genuine_signals = category_data['authenticity_signals']['genuine']
    staged_warnings = category_data['authenticity_signals']['staged_warnings']
    
    genuine_count = sum(1 for signal in genuine_signals if signal in all_text['comments'])
    staged_count = sum(1 for warning in staged_warnings if warning in all_text['comments'] or warning in all_text['title'])
    
    if genuine_count > staged_count:
        score += min(genuine_count * 0.15, 0.4)
    
    if staged_count > 0:
        score -= min(staged_count * 0.2, 0.3)
    
    return max(min(score, 1.0), 0.0)

def assess_emotional_impact(all_text, comment_sentiment, content_type):
    """Assess emotional impact on viewers"""
    score = 0.3
    
    if comment_sentiment['total'] > 0:
        positive_ratio = comment_sentiment['positive'] / comment_sentiment['total']
        emotional_intensity = comment_sentiment.get('emotional_intensity', 0)
        
        score += positive_ratio * 0.4
        score += min(emotional_intensity / 100, 0.3)
    
    strong_emotions = ['crying', 'tears', 'emotional', 'touching', 'beautiful', 'moving', 'powerful']
    emotion_matches = sum(1 for emotion in strong_emotions if emotion in all_text['comments'])
    
    if emotion_matches > 5:
        score += 0.3
    elif emotion_matches > 2:
        score += 0.2
    
    return min(score, 1.0)

def assess_content_type(all_text, content_types):
    """Assess if content matches expected types"""
    score = 0.2
    
    total_matches = 0
    for content_type, keywords in content_types.items():
        matches = sum(1 for kw in keywords if kw in all_text['title'] or kw in all_text['description'] or kw in all_text['comments'])
        total_matches += matches
    
    if total_matches > 5:
        score += 0.6
    elif total_matches > 2:
        score += 0.4
    elif total_matches > 0:
        score += 0.2
    
    return min(score, 1.0)

def assess_viewer_response(moments, comment_sentiment):
    """Assess viewer response quality"""
    score = 0.3
    
    if moments:
        high_quality_moments = len([m for m in moments if m['relevance_score'] >= 5.0])
        if high_quality_moments >= 3:
            score += 0.5
        elif high_quality_moments >= 1:
            score += 0.3
        elif len(moments) >= 3:
            score += 0.2
    
    if comment_sentiment['total'] > 20:
        score += 0.2
    
    return min(score, 1.0)

def assess_visual_warmth(thumbnail_analysis):
    """Assess visual warmth for heartwarming content"""
    score = 0.5
    
    if thumbnail_analysis['available']:
        if thumbnail_analysis['color_profile']['warm_tones']:
            score += 0.3
        if thumbnail_analysis['brightness'] > 140:
            score += 0.2
    
    return min(score, 1.0)

def assess_speech_content(transcript_text, speech_patterns):
    """Assess speech content from transcript"""
    if not transcript_text:
        return 0.5
    
    score = 0.4
    
    for pattern_type, phrases in speech_patterns.items():
        matches = sum(1 for phrase in phrases if phrase in transcript_text)
        if matches > 0:
            score += min(matches * 0.1, 0.2)
    
    return min(score, 1.0)

def comprehensive_category_analysis(data, category_key):
    """Comprehensive analysis tailored to specific category"""
    
    category_data = SPECIALIZED_CATEGORIES[category_key]
    
    # Extract all text data
    all_text = {
        'title': data['title'].lower(),
        'description': data['description'].lower(),
        'comments': ' '.join(data['comments']).lower(),
        'transcript': data['transcript']['text'].lower() if data['transcript']['available'] else '',
        'channel_desc': data['channel_info']['description'].lower()
    }
    
    # Extract timestamped moments
    timestamped_moments = extract_timestamped_moments(data['comments'], category_key)
    
    # Basic analysis components
    components = {
        'authenticity': assess_authenticity(all_text, category_data, 'heartwarming'),
        'emotional_impact': assess_emotional_impact(all_text, data['comment_sentiment'], 'heartwarming'),
        'content_type_match': assess_content_type(all_text, category_data['content_types']),
        'viewer_response': assess_viewer_response(timestamped_moments, data['comment_sentiment']),
        'visual_warmth': assess_visual_warmth(data['thumbnail_analysis']),
        'speech_analysis': assess_speech_content(all_text['transcript'], category_data['speech_patterns'])
    }
    
    # Calculate weighted score
    weights = {
        'authenticity': 0.25,
        'emotional_impact': 0.25,
        'content_type_match': 0.20,
        'viewer_response': 0.15,
        'visual_warmth': 0.08,
        'speech_analysis': 0.07
    }
    
    base_score = 3.0
    component_contribution = sum(components[key] * weights[key] for key in weights) * 7.0
    final_score = base_score + component_contribution
    
    # Authenticity penalty
    if components['authenticity'] < 0.4:
        final_score *= 0.7
    
    # High quality moment bonus
    high_quality_moments = len([m for m in timestamped_moments if m['relevance_score'] >= 5.0])
    if high_quality_moments >= 2:
        final_score += 0.8
    
    confidence = 0.3
    if len(data['comments']) > 20:
        confidence += 0.25
    if data['transcript']['available']:
        confidence += 0.2
    if len(timestamped_moments) > 0:
        confidence += 0.15
    if components['authenticity'] > 0.6:
        confidence += 0.1
    
    # Extract key indicators
    indicators = []
    for content_type, keywords in category_data['content_types'].items():
        found = [kw for kw in keywords if kw in all_text['comments'] or kw in all_text['title']]
        if found:
            indicators.extend(found[:2])
    
    return {
        'final_score': min(final_score, 10.0),
        'component_scores': components,
        'confidence': min(confidence, 1.0),
        'timestamped_moments': timestamped_moments,
        'authenticity_assessment': 'authentic' if components['authenticity'] > 0.7 else 'questionable' if components['authenticity'] > 0.4 else 'likely_staged',
        'key_indicators': indicators[:6],
        'data_sources': {
            'comments': len(data['comments']),
            'transcript': data['transcript']['available'],
            'engagement_data': data['viewCount'] > 0,
            'thumbnail': data['thumbnail_analysis']['available']
        }
    }

def get_score_color(score):
    """Get color indicator based on score"""
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
        <p><strong>Advanced Analysis for Heartwarming, Motivational & Traumatic Content</strong></p>
        <small>Multi-source analysis with transcript data and category-specific algorithms</small>
    </div>
    """, unsafe_allow_html=True)
    
    # Category selection
    st.subheader("📋 Select Content Category")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("❤️ Heartwarming Content", help="Touching, emotional, positive moments", use_container_width=True):
            st.session_state.selected_category = 'heartwarming_content'
    
    with col2:
        if st.button("💪 Motivational Content", help="Inspiring achievements and transformation", use_container_width=True):
            st.session_state.selected_category = 'motivational_content'
    
    with col3:
        if st.button("⚠️ Traumatic Events", help="Serious events with significant impact", use_container_width=True):
            st.session_state.selected_category = 'traumatic_events'
    
    # Show selected category
    selected_category = st.session_state.get('selected_category', 'heartwarming_content')
    category_info = SPECIALIZED_CATEGORIES[selected_category]
    
    st.markdown(f"""
    <div class="category-card">
        <h3>{category_info['emoji']} {category_info['name']}</h3>
        <p>{category_info['description']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Configuration sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        api_key = st.text_input(
            "YouTube Data API v3 Key",
            type="password",
            help="Required for comprehensive analysis"
        )
        
        if not api_key:
            st.warning("🔑 API key required")
            st.info("Get your key at: https://console.developers.google.com/")
        
        st.markdown("---")
        st.subheader("🔍 Analysis Features")
        st.markdown(f"""
        **Current Category:** {category_info['emoji']} {category_info['name']}
        
        **Data Sources:**
        • ✅ Video metadata & engagement
        • ✅ Enhanced comment analysis  
        • ✅ Transcript/audio analysis
        • ✅ Thumbnail visual analysis
        • ✅ Channel credibility assessment
        
        **Category-Specific Analysis:**
        • 🎯 Content type matching
        • 🔍 Authenticity assessment
        • 📊 Viewer impact measurement
        • ⚡ Specialized scoring algorithm
        """)
    
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
        analyze_button = st.button(
            "🚀 Analyze Content",
            disabled=not api_key or not video_url,
            use_container_width=True
        )
    
    if analyze_button and video_url:
        video_id = extract_video_id(video_url)
        
        if not video_id:
            st.error("❌ Invalid YouTube URL")
        else:
            try:
                # Progress tracking
                progress_text = st.empty()
                progress_bar = st.progress(0)
                
                progress_text.text("🔍 Fetching video data...")
                progress_bar.progress(20)
                
                # Fetch comprehensive data
                video_data = fetch_comprehensive_data(video_id, api_key)
                
                progress_text.text("🎙️ Analyzing transcript & audio...")
                progress_bar.progress(50)
                
                # Run specialized analysis
                analysis_result = comprehensive_category_analysis(video_data, selected_category)
                
                progress_text.text("🧠 Running category-specific analysis...")
                progress_bar.progress(80)
                
                progress_bar.progress(100)
                progress_text.text("✅ Specialized analysis complete!")
                time.sleep(0.8)
                progress_text.empty()
                progress_bar.empty()
                
                # Display results
                st.success("🎉 Specialized Analysis Complete!")
                
                # Data sources summary
                data_sources = analysis_result['data_sources']
                st.info(f"""
                📊 **Analysis Sources:** Comments: {data_sources['comments']} | 
                Transcript: {'✅' if data_sources['transcript'] else '❌'} | 
                Thumbnail: {'✅' if data_sources['thumbnail'] else '❌'} | 
                Engagement: {'✅' if data_sources['engagement_data'] else '❌'}
                """)
                
                # Main results
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"### 📺 {video_data['title']}")
                    st.markdown(f"**Channel:** {video_data['channelTitle']}")
                    st.markdown(f"**Duration:** {video_data['duration']} | **Published:** {video_data['publishedAt'][:10]}")
                    
                    # Stats
                    col_a, col_b, col_c, col_d = st.columns(4)
                    with col_a:
                        st.metric("👀 Views", f"{video_data['viewCount']:,}")
                    with col_b:
                        st.metric("👍 Likes", f"{video_data['likeCount']:,}")
                    with col_c:
                        st.metric("💬 Comments", f"{video_data['commentCount']:,}")
                    with col_d:
                        if video_data['viewCount'] > 0:
                            engagement = (video_data['likeCount'] + video_data['commentCount']) / video_data['viewCount'] * 100
                            st.metric("📈 Engagement", f"{engagement:.2f}%")
                
                with col2:
                    # Score display
                    score = analysis_result['final_score']
                    confidence = analysis_result['confidence']
                    score_emoji = get_score_color(score)
                    
                    st.markdown(f"""
                    <div class="score-card">
                        <h2>{category_info['emoji']} Category Score</h2>
                        <h1 style="margin: 0; font-size: 4rem;">{score:.1f}</h1>
                        <h3>/10</h3>
                        <p style="margin: 0.5rem 0;">Confidence: {confidence:.0%}</p>
                        <small>Specialized {category_info['name']} Analysis</small>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Authenticity assessment
                authenticity = analysis_result['authenticity_assessment']
                if authenticity == 'authentic':
                    st.success("✅ **AUTHENTIC CONTENT** - Appears genuine and unscripted")
                elif authenticity == 'questionable':
                    st.warning("⚠️ **QUESTIONABLE AUTHENTICITY** - Some staged elements detected")
                elif authenticity == 'likely_staged':
                    st.error("❌ **LIKELY STAGED** - Multiple indicators of artificial content")
                
                # Component breakdown
                st.subheader("📊 Analysis Components")
                
                components = analysis_result['component_scores']
                
                component_info = [
                    ('authenticity', 'Authenticity', '🔍', 'How genuine the content appears'),
                    ('emotional_impact', 'Emotional Impact', '❤️', 'Viewer emotional response strength'),
                    ('content_type_match', 'Content Type', '🎯', 'Matches expected content types'),
                    ('viewer_response', 'Viewer Response', '💬', 'Quality of viewer reactions'),
                    ('visual_warmth', 'Visual Appeal', '🌟', 'Visual indicators and quality'),
                    ('speech_analysis', 'Speech Content', '🎙️', 'Audio/speech pattern analysis')
                ]
                
                for key, name, emoji, description in component_info:
                    if key in components:
                        component_score = components[key] * 10
                        color = get_score_color(component_score)
                        
                        st.markdown(f"""
                        <div class="component-card">
                            <h4>{emoji} {name} {color} {component_score:.1f}/10</h4>
                            <p style="margin: 0; color: #6c757d; font-size: 0.9em;">{description}</p>
                        </div>
                        """, unsafe_allow_html=True)
                
                # Key indicators found
                if analysis_result['key_indicators']:
                    st.subheader("🎯 Key Indicators Detected")
                    
                    for indicator in analysis_result['key_indicators']:
                        st.markdown(f"""
                        <span class="authenticity-indicator authentic">{indicator}</span>
                        """, unsafe_allow_html=True)
                
                # Timestamped moments
                moments = analysis_result['timestamped_moments']
                if moments:
                    st.subheader("⏰ Key Moments Identified by Viewers")
                    
                    for moment in moments[:5]:
                        quality_emoji = "🌟" if moment['relevance_score'] >= 6.0 else "⭐" if moment['relevance_score'] >= 3.0 else "🟡"
                        
                        st.markdown(f"""
                        <div class="moment-highlight">
                            <strong>⏰ {moment['timestamp']}</strong> {quality_emoji} 
                            <span style="color: #28a745; font-weight: bold;">Relevance: {moment['relevance_score']:.1f}</span><br>
                            <em>"{moment['comment'][:150]}{'...' if len(moment['comment']) > 150 else ''}"</em><br>
                            <small><strong>Found:</strong> {', '.join(moment['category_indicators']['emotions'][:3]) if moment['category_indicators']['emotions'] else 'General relevance'}</small>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    if len(moments) > 5:
                        st.info(f"💡 {len(moments) - 5} additional moments found")
                else:
                    st.warning("⚠️ No timestamped moments found - manual review recommended")
                
                # Transcript analysis (if available)
                if video_data['transcript']['available']:
                    with st.expander("🎙️ Transcript Analysis"):
                        st.success(f"✅ Transcript available ({video_data['transcript']['source']})")
                        
                        # Show transcript segments if available
                        if video_data['transcript'].get('segments'):
                            st.write("**Key Transcript Segments:**")
                            segments = video_data['transcript']['segments'][:6]
                            
                            for segment in segments:
                                start_time = int(segment['start'])
                                minutes = start_time // 60
                                seconds = start_time % 60
                                
                                st.markdown(f"""
                                <div class="transcript-segment">
                                    <strong>{minutes}:{seconds:02d}</strong> - "{segment['text']}"
                                </div>
                                """, unsafe_allow_html=True)
                        else:
                            # Show partial transcript text
                            transcript_preview = video_data['transcript']['text'][:500]
                            st.markdown(f"""
                            <div class="transcript-segment">
                                <strong>Transcript Preview:</strong><br>
                                "{transcript_preview}{'...' if len(video_data['transcript']['text']) > 500 else ''}"
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    st.warning("⚠️ No transcript available - analysis based on metadata and comments only")
                
                # Final assessment
                st.subheader("🎯 Final Assessment")
                
                if score >= 8.5:
                    st.success("🌟 **EXCELLENT MATCH** - Outstanding example of this category")
                    assessment = f"This video is an excellent example of {category_info['name'].lower()} with strong authenticity and clear category fit."
                elif score >= 7.0:
                    st.success("✅ **STRONG MATCH** - Good example of this category")
                    assessment = f"This video shows strong characteristics of {category_info['name'].lower()} with good viewer engagement."
                elif score >= 5.5:
                    st.info("⚠️ **MODERATE MATCH** - Some category elements present")
                    assessment = f"This video has some elements of {category_info['name'].lower()} but may not be the strongest example."
                elif score >= 3.5:
                    st.warning("🟠 **WEAK MATCH** - Limited category alignment")
                    assessment = f"This video shows limited alignment with {category_info['name'].lower()} characteristics."
                else:
                    st.error("❌ **POOR MATCH** - Does not fit this category well")
                    assessment = f"This video does not appear to be a good fit for {category_info['name'].lower()}."
                
                st.write(assessment)
                
                # Save analysis
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("💾 Save Analysis"):
                        analysis_summary = {
                            'timestamp': datetime.now().isoformat(),
                            'video_id': video_id,
                            'title': video_data['title'],
                            'category': selected_category,
                            'score': score,
                            'confidence': confidence,
                            'authenticity': analysis_result['authenticity_assessment'],
                            'moments_found': len(moments),
                            'transcript_available': video_data['transcript']['available']
                        }
                        st.session_state.analysis_history.append(analysis_summary)
                        st.success("✅ Analysis saved!")
                
                with col2:
                    # Export detailed report
                    report_data = {
                        'analysis_metadata': {
                            'timestamp': datetime.now().isoformat(),
                            'category': selected_category,
                            'analyzer_version': 'Specialized v3.0'
                        },
                        'video_info': {
                            'id': video_id,
                            'title': video_data['title'],
                            'channel': video_data['channelTitle']
                        },
                        'results': {
                            'final_score': score,
                            'confidence': confidence,
                            'authenticity': analysis_result['authenticity_assessment'],
                            'component_scores': analysis_result['component_scores']
                        },
                        'evidence': {
                            'key_indicators': analysis_result['key_indicators'],
                            'top_moments': moments[:3],
                            'transcript_available': video_data['transcript']['available']
                        }
                    }
                    
                    json_str = json.dumps(report_data, indent=2, default=str)
                    st.download_button(
                        label="📄 Export Report",
                        data=json_str,
                        file_name=f"specialized_analysis_{video_id}.json",
                        mime="application/json"
                    )
                
                with col3:
                    st.markdown(f"[🎥 **Watch Video**]({video_url})")
                
            except Exception as e:
                st.error(f"❌ Analysis failed: {str(e)}")
                
                if "403" in str(e):
                    st.info("💡 **API Issue:** Check your YouTube Data API v3 key")
                elif "429" in str(e):
                    st.info("💡 **Rate Limited:** Try again later")
                else:
                    st.info("💡 **Error:** Check video URL and try again")
    
    # Analysis History
    if st.session_state.analysis_history:
        st.markdown("---")
        st.header("📚 Analysis History")
        
        # Summary stats
        total = len(st.session_state.analysis_history)
        avg_score = sum(a['score'] for a in st.session_state.analysis_history) / total
        excellent_count = sum(1 for a in st.session_state.analysis_history if a['score'] >= 8.5)
        authentic_count = sum(1 for a in st.session_state.analysis_history if a.get('authenticity') == 'authentic')
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📊 Total", total)
        with col2:
            st.metric("⭐ Avg Score", f"{avg_score:.1f}")
        with col3:
            st.metric("🌟 Excellent", excellent_count)
        with col4:
            st.metric("✅ Authentic", authentic_count)
        
        # History table
        df = pd.DataFrame([
            {
                'Date': datetime.fromisoformat(a['timestamp']).strftime('%m/%d %H:%M'),
                'Title': a['title'][:30] + '...' if len(a['title']) > 30 else a['title'],
                'Category': a['category'].replace('_', ' ').title()[:12],
                'Score': f"{a['score']:.1f}",
                'Confidence': f"{a['confidence']:.0%}",
                'Authenticity': a.get('authenticity', 'unknown')[:10],
                'Moments': a['moments_found'],
                'Transcript': '✅' if a['transcript_available'] else '❌'
            }
            for a in reversed(st.session_state.analysis_history[-12:])
        ])
        
        st.dataframe(df, use_container_width=True)
        
        if st.button("🗑️ Clear History"):
            st.session_state.analysis_history = []
            st.rerun()
    
    # Footer with category baselines
    st.markdown("---")
    st.subheader("📊 Category Scoring Baselines")
    
    tab1, tab2, tab3 = st.tabs(["❤️ Heartwarming", "💪 Motivational", "⚠️ Traumatic"])
    
    with tab1:
        st.markdown("""
        **🌟 Excellent (8.5-10):** Genuine reunions, life-saving acts, authentic emotional moments
        **✅ Good (7.0-8.4):** Sweet family moments, acts of kindness, positive surprises  
        **⚠️ Moderate (5.5-6.9):** Mildly positive content, questionable authenticity
        **❌ Poor (0-5.4):** Staged content, fake emotions, manipulation attempts
        
        **Key Factors:** Authenticity > Emotional Impact > Content Type Match
        """)
    
    with tab2:
        st.markdown("""
        **🌟 Excellent (8.5-10):** Documented transformation, overcoming major adversity, authentic struggle-to-success
        **✅ Good (7.0-8.4):** Real achievements, inspiring journeys, actionable advice
        **⚠️ Moderate (5.5-6.9):** Some motivational elements, limited authenticity
        **❌ Poor (0-5.4):** Fake guru content, toxic positivity, get-rich-quick schemes
        
        **Key Factors:** Achievement Authenticity > Struggle Narrative > Inspirational Impact
        """)
    
    with tab3:
        st.markdown("""
        **🌟 Excellent (8.5-10):** Responsible news coverage, educational trauma content, survivor stories
        **✅ Good (7.0-8.4):** Serious events with appropriate context, awareness content
        **⚠️ Moderate (5.5-6.9):** Somewhat serious content, questionable presentation
        **❌ Poor (0-5.4):** Exploitative content, sensationalized trauma, clickbait tragedy
        
        **Key Factors:** Responsible Handling > Event Severity > Educational Value
        """)

if __name__ == "__main__":
    main()
