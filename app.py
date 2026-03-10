import streamlit as st
import openai
import os
from dotenv import load_dotenv
import requests
from youtube_transcript_api import YouTubeTranscriptApi
import re
from tavily import TavilyClient
import validators
import time
from datetime import datetime
import random
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

# Initialize API keys
AZURE_API_KEY = os.getenv("AZURE_API_KEY", "b07ae056-6feb-4db0-b3d4-35d95e7cad32")
AZURE_ENDPOINT = os.getenv(
    "AZURE_ENDPOINT",
    "https://genai-nexus.api.corpinter.net/apikey",
)
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "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")

# Initialize Tavily client
tavily = TavilyClient(api_key=TAVILY_API_KEY)

# Configure OpenAI
openai.api_type = "azure"
openai.api_key = AZURE_API_KEY
openai.api_base = AZURE_ENDPOINT
openai.api_version = "2024-10-21"

# Azure OpenAI Deployment Name
AZURE_DEPLOYMENT_NAME = "gpt-5"

# Free proxy list for YouTube requests
PROXY_LIST = [
    "https://api.allorigins.win/raw?url=",
    "https://api.codetabs.com/v1/proxy?quest="
]

# Page configuration
st.set_page_config(
    page_title="Gaurav's Linkedin Post",
    page_icon="📝",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .main { padding: 2rem; }
    .stButton>button {
        background-color: #0a66c2;
        color: white;
        border-radius: 24px;
        padding: 10px 20px;
        font-weight: 600;
        width: 100%;
    }
    .stTextArea>div>div>textarea {
        background-color: #f3f6f9;
    }
    .source-info {
        padding: 15px;
        background-color: #f8f9fa;
        border-radius: 8px;
        margin: 15px 0;
        border-left: 4px solid #0a66c2;
    }
    .content-box {
        padding: 20px;
        background-color: white;
        border-radius: 8px;
        border: 1px solid #e1e4e8;
        margin: 10px 0;
    }
    .content-comparison {
        display: flex;
        gap: 20px;
        margin: 20px 0;
    }
    </style>
    """, unsafe_allow_html=True)

def summarize_content(text, title=""):
    """Summarize content using Azure OpenAI"""
    try:
        messages = [
            {"role": "system", "content": "You are a professional content summarizer. Create a concise summary that captures the main points and key insights."},
            {"role": "user", "content": f"Title: {title}\n\nContent to summarize:\n{text}"}
        ]

        response = openai.ChatCompletion.create(
            engine=AZURE_DEPLOYMENT_NAME,
            messages=messages,
            # temperature=0.5,
            max_completion_tokens=4000,
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Error summarizing content: {str(e)}")
        return None

def extract_statistics_and_quotes(text):
    """Extract statistics and quotes from text using Azure OpenAI"""
    try:
        messages = [
            {"role": "system", "content": "You are a data analyst. Extract key statistics, numbers, and notable quotes from the given text. Format them as bullet points."},
            {"role": "user", "content": f"Extract statistics and quotes from:\n{text}"}
        ]

        response = openai.ChatCompletion.create(
            engine=AZURE_DEPLOYMENT_NAME,
            messages=messages,
            # temperature=0.3,
            max_completion_tokens=4000,
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        return ""

def get_web_search_results(topic):
    """Get web search results using Tavily API with enhanced processing"""
    try:
        # First search for statistics and data
        stats_search = tavily.search(
            query=f"statistics data numbers facts about {topic}",
            search_depth="advanced",
            include_domains=["linkedin.com", "medium.com", "forbes.com", "entrepreneur.com", "inc.com", "statista.com", "bloomberg.com"],
            max_results=3
        )
        
        # Then search for general content
        general_search = tavily.search(
            query=topic,
            search_depth="advanced",
            include_domains=["linkedin.com", "medium.com", "forbes.com", "entrepreneur.com", "inc.com"],
            include_answer=True,
            max_results=3
        )
        
        if stats_search and general_search:
            sources = []
            content = []
            stats = []
            
            # Process statistics search
            for result in stats_search.get('results', []):
                stats.append(result.get('content', ''))
                sources.append({
                    'title': result.get('title', 'Untitled'),
                    'url': result.get('url', ''),
                    'published_date': result.get('published_date', ''),
                    'type': 'Statistics Source'
                })

            # Process general search
            if 'answer' in general_search and general_search['answer']:
                content.append(general_search['answer'])
            
            for result in general_search.get('results', []):
                content.append(result.get('content', ''))
                sources.append({
                    'title': result.get('title', 'Untitled'),
                    'url': result.get('url', ''),
                    'published_date': result.get('published_date', ''),
                    'type': 'General Source'
                })
            
            # Extract statistics and quotes
            stats_and_quotes = extract_statistics_and_quotes("\n".join(stats))
            
            return {
                'content': "\n\n".join(content),
                'statistics': stats_and_quotes,
                'sources': sources
            }
        return None
    except Exception as e:
        st.error(f"Error in web search: {str(e)}")
        return None

def extract_youtube_id(url):
    """Extract YouTube video ID from URL"""
    patterns = [
        r'(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_youtube_video_info(video_id):
    """Get YouTube video title and channel name"""
    try:
        api_url = f"https://www.googleapis.com/youtube/v3/videos?id={video_id}&key=AIzaSyDz8YY8oFe9YGEYe3_0IzOZrYWnm6wKCyM&part=snippet"
        response = requests.get(api_url)
        data = response.json()
        
        if 'items' in data and len(data['items']) > 0:
            snippet = data['items'][0]['snippet']
            return {
                'title': snippet['title'],
                'channel': snippet['channelTitle'],
                'published_date': snippet['publishedAt'][:10]
            }
    except Exception:
        pass
    return None

def get_youtube_transcript_with_proxy(video_id):
    """Get YouTube transcript using proxy servers"""
    errors = []
    
    # Try direct access first
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([item['text'] for item in transcript_list])
    except Exception as e:
        errors.append(str(e))

    # Try with each proxy
    for proxy in PROXY_LIST:
        try:
            time.sleep(2)  # Respect rate limits
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, proxies={'http': proxy, 'https': proxy})
            return " ".join([item['text'] for item in transcript_list])
        except Exception as e:
            errors.append(str(e))
            continue

    st.error(f"Could not get transcript. Errors: {'; '.join(errors)}")
    return None

def get_url_content(url):
    """Get content from URL using requests"""
    try:
        response = requests.get(url)
        if response.status_code == 200:
            # Use Tavily to extract main content
            search_result = tavily.search(query=f"summarize the content from {url}")
            if search_result and 'results' in search_result and len(search_result['results']) > 0:
                result = search_result['results'][0]
                return {
                    'content': result['content'],
                    'title': result.get('title', 'Article'),
                    'url': url,
                    'published_date': result.get('published_date', '')
                }
        st.error("Could not extract content from the URL")
        return None
    except Exception as e:
        st.error(f"Error getting URL content: {str(e)}")
        return None

def display_sources(sources, title="Sources Used"):
    """Display sources in a formatted way"""
    st.markdown(f"### 📚 {title}")
    for source in sources:
        published_date = source.get('published_date', '')
        date_str = f"Published: {published_date}" if published_date else ""
        
        st.markdown(f"""
        <div class="source-info">
            <strong>{source['title']}</strong><br>
            {date_str}<br>
            <a href="{source['url']}" target="_blank">Read More</a>
        </div>
        """, unsafe_allow_html=True)

def generate_linkedin_post(content, tone="professional", content_type="topic", source_info=None):
    """Generate LinkedIn post using Azure OpenAI with enhanced prompting"""
    try:
        context = ""
        stats = ""
        
        if isinstance(content, dict):
            if 'sources' in content:  # Web search results
                stats = f"\n\nKey Statistics and Quotes:\n{content.get('statistics', '')}"
                context = f"\n\nBased on the following research:\n{content['content']}{stats}"
            elif 'content' in content:  # URL content
                context = f"\n\nBased on the article: '{content['title']}'\n{content['content']}"
            elif 'text' in content:  # YouTube content
                video_info = f"Video: '{content.get('title', 'YouTube video')}' by {content.get('channel', 'Unknown channel')}\n"
                context = f"\n\nBased on the video transcript:\n{video_info}{content['text']}"
        else:
            context = content

        messages = [
            {"role": "system", "content": f"""You are an expert LinkedIn content creator specializing in data-driven, engaging posts.
            Create a compelling post with the following tone: {tone}
            
            Required elements:
            1. Start with an attention-grabbing statistic or surprising fact
            2. Include 2-3 concise, value-packed paragraphs
            3. Incorporate relevant statistics and data points
            4. Add a thought-provoking quote if available
            5. End with a clear call-to-action
            6. Include 3-5 relevant, trending hashtags
            
            Make it professional, insightful, and backed by data. Focus on providing actionable value to readers."""},
            {"role": "user", "content": f"Create a LinkedIn post about: {context}"}
        ]

        response = openai.ChatCompletion.create(
            engine=AZURE_DEPLOYMENT_NAME,
            messages=messages,
            # temperature=0.7,
            max_completion_tokens=4000,
            # top_p=1,
            # frequency_penalty=0,
            # presence_penalty=0,
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Error generating post: {str(e)}")
        return None

# Main content area
st.title("🚀 Gaurav's Linkedin Post")
st.markdown("### Transform Your Ideas into Engaging LinkedIn Content")

# Input type selection
input_type = st.radio("Choose Input Type:", ["Topic (Web Research)", "URL", "YouTube Video"])

# Input section with columns
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("### Enter Your Content")
    if input_type == "Topic (Web Research)":
        user_input = st.text_area(
            "What would you like to create a post about?",
            height=150,
            placeholder="Enter your topic for web research..."
        )
    else:
        user_input = st.text_input(
            "Enter URL:",
            placeholder="Paste your URL here..."
        )

with col2:
    st.markdown("### Customize Your Post")
    tone = st.selectbox(
        "Select Tone:",
        ["Professional", "Conversational", "Technical", "Inspirational", "Analytical"],
        index=0
    )

# Generate button
if st.button("Generate Post ✨", use_container_width=True):
    if user_input:
        with st.spinner("✍️ Researching and crafting your LinkedIn post..."):
            content = None
            content_type = "topic"
            source_info = None

            # Process input based on type
            if input_type == "Topic (Web Research)":
                search_results = get_web_search_results(user_input)
                if search_results:
                    content = search_results
                    source_info = {
                        'type': 'web_research',
                        'sources': search_results['sources']
                    }
            elif input_type == "YouTube Video":
                if not validators.url(user_input):
                    st.error("Please enter a valid YouTube URL")
                else:
                    video_id = extract_youtube_id(user_input)
                    if video_id:
                        content = get_youtube_transcript_with_proxy(video_id)
                        if content:
                            # Summarize transcript
                            summary = summarize_content(content, '')
                            if summary:
                                content = summary
                                content_type = "youtube"
                                source_info = {
                                    'type': 'youtube',
                                    'url': user_input,
                                    'title': content.split('\n')[0],
                                    'channel': content.split('\n')[1],
                                    'published_date': content.split('\n')[2]
                                }
                    else:
                        st.error("Invalid YouTube URL")
            else:  # URL
                if not validators.url(user_input):
                    st.error("Please enter a valid URL")
                else:
                    content = get_url_content(user_input)
                    if content:
                        # Summarize content
                        summary = summarize_content(content['content'], content['title'])
                        if summary:
                            content['content'] = summary
                            content_type = "url"
                            source_info = {
                                'type': 'url',
                                'url': content['url'],
                                'title': content['title'],
                                'published_date': content.get('published_date', '')
                            }

            if content:
                # Display source information
                if source_info:
                    if source_info['type'] == 'web_research':
                        display_sources(source_info['sources'], "Research Sources")
                    else:
                        st.markdown("### 📚 Source Information")
                        published_date = source_info.get('published_date', '')
                        date_str = f"Published: {published_date}" if published_date else ""
                        
                        st.markdown(f"""
                        <div class="source-info">
                            <strong>{source_info['title']}</strong><br>
                            {date_str}<br>
                            <a href="{source_info['url']}" target="_blank">View Source</a>
                        </div>
                        """, unsafe_allow_html=True)

                # Generate post
                post_content = generate_linkedin_post(content, tone.lower(), content_type)
                if post_content:
                    st.markdown("### 📝 Generated LinkedIn Post")
                    st.markdown('<div class="content-box">', unsafe_allow_html=True)
                    st.markdown(post_content)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Store in session state
                    if 'posts' not in st.session_state:
                        st.session_state.posts = []
                    
                    st.session_state.posts.append({
                        'content': post_content,
                        'source_info': source_info,
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    
                    # Refinement options
                    st.markdown("---")
                    st.markdown("### ✨ Refine Your Post")
                    
                    # Show original post in a box
                    st.markdown("#### Current Version")
                    st.markdown('<div class="content-box">', unsafe_allow_html=True)
                    st.markdown(post_content)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Refinement options
                    col1, col2 = st.columns([1, 1])
                    
                    with col1:
                        refinement = st.multiselect(
                            "Quick Refinement Options:",
                            ["Make it shorter", "Make it longer", "Add more hashtags", 
                             "Make it more professional", "Add statistics", 
                             "Add more data points", "Include market trends",
                             "Add industry insights"]
                        )
                    
                    with col2:
                        custom_instructions = st.text_area(
                            "Custom Refinement Instructions:",
                            placeholder="Enter specific instructions for how you'd like to improve the post..."
                        )
                    
                    if refinement or custom_instructions:
                        if st.button("Refine Post ✨", key="refine_button", use_container_width=True):
                            with st.spinner("🔄 Refining your post..."):
                                instructions = []
                                if refinement:
                                    instructions.append(f"Apply these refinements: {', '.join(refinement)}")
                                if custom_instructions:
                                    instructions.append(f"Additional instructions: {custom_instructions}")
                                
                                refinement_prompt = f"""Please improve this LinkedIn post with the following changes:
                                {' '.join(instructions)}
                                
                                Original post:
                                {post_content}
                                
                                Create a new version that maintains the core message but incorporates the requested improvements."""
                                
                                refined_content = generate_linkedin_post(refinement_prompt, tone.lower(), "topic")
                                if refined_content:
                                    st.markdown("### 📝 Post Comparison")
                                    
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        st.markdown("#### Original Post")
                                        st.markdown('<div class="content-box">', unsafe_allow_html=True)
                                        st.markdown(post_content)
                                        st.markdown('</div>', unsafe_allow_html=True)
                                        if source_info:
                                            st.markdown("**Sources Used:**")
                                            display_sources([source_info] if not isinstance(source_info.get('sources', []), list) else source_info['sources'])
                                    
                                    with col2:
                                        st.markdown("#### Refined Post")
                                        st.markdown('<div class="content-box">', unsafe_allow_html=True)
                                        st.markdown(refined_content)
                                        st.markdown('</div>', unsafe_allow_html=True)
                                        st.markdown("**Improvements Made:**")
                                        if refinement:
                                            st.markdown("- " + "\n- ".join(refinement))
                                        if custom_instructions:
                                            st.markdown(f"- Custom improvements: {custom_instructions}")
                                        
                                    # Store refined version
                                    st.session_state.posts.append({
                                        'content': refined_content,
                                        'source_info': source_info,
                                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        'refinement_options': refinement,
                                        'custom_instructions': custom_instructions
                                    })
    else:
        st.warning(f"Please enter a {'topic' if input_type == 'Topic (Web Research)' else 'URL'}.") 
