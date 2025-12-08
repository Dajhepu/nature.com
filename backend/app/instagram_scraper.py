import requests
import json
from flask import current_app

BASE_URL = "https://www.instagram.com/api/v1"

def get_common_headers():
    """Returns headers that mimic a real browser to avoid blocks."""
    session_id = current_app.config.get('INSTAGRAM_SESSIONID')
    if not session_id:
        raise ValueError("INSTAGRAM_SESSIONID not configured.")

    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36',
        'X-IG-App-ID': '936619743392459',
        'Cookie': f'sessionid={session_id}',
    }

async def make_instagram_request(endpoint):
    """Makes an authenticated request to a specific Instagram API endpoint."""
    headers = get_common_headers()
    url = f"{BASE_URL}{endpoint}"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        if response.status_code == 403:
            print("Forbidden: Check if session ID is valid or expired.")
        return None
    except Exception as err:
        print(f"An error occurred: {err}")
        return None

async def get_user_profile(username):
    """Fetches profile data for a given Instagram username."""
    endpoint = f"/users/web_profile_info/?username={username}"
    data = await make_instagram_request(endpoint)

    if not data or 'data' not in data or 'user' not in data['data']:
        print(f"Could not retrieve profile for {username}.")
        return None

    user_data = data['data']['user']

    return {
        'user_id': user_data.get('id'),
        'username': user_data.get('username'),
        'full_name': user_data.get('full_name'),
        'biography': user_data.get('biography'),
        'followers_count': user_data['edge_followed_by']['count'],
        'following_count': user_data['edge_follow']['count'],
        'posts_count': user_data['edge_owner_to_timeline_media']['count'],
        'is_private': user_data.get('is_private'),
    }

async def get_user_posts(user_id, max_posts=50):
    """Fetches all posts for a given user ID, up to a max limit."""
    all_posts = []
    variables = {"id": user_id, "first": 50}
    has_next_page = True

    while has_next_page and len(all_posts) < max_posts:
        endpoint = f"/graphql/query/?query_hash=e769aa130647d2354c40ea6a439bfc08&variables={json.dumps(variables)}"
        data = await make_instagram_request(endpoint)

        if not data or 'data' not in data or 'user' not in data['data']:
            break

        media = data['data']['user']['edge_owner_to_timeline_media']
        page_info = media['page_info']

        for edge in media['edges']:
            node = edge['node']
            all_posts.append({
                'media_id': node['id'],
                'shortcode': node['shortcode'],
                'text': node['edge_media_to_caption']['edges'][0]['node']['text'] if node['edge_media_to_caption']['edges'] else '',
                'likes_count': node['edge_media_preview_like']['count'],
                'comments_count': node['edge_media_to_comment']['count'],
                'media_url': node['display_url'],
                'timestamp': node['taken_at_timestamp'],
            })
            if len(all_posts) >= max_posts:
                break

        has_next_page = page_info['has_next_page']
        if has_next_page:
            variables['after'] = page_info['end_cursor']

    return all_posts

async def get_post_comments(shortcode, max_comments=100):
    """Fetches comments for a given post shortcode."""
    all_comments = []
    variables = {"shortcode": shortcode, "first": 50}
    has_next_page = True

    while has_next_page and len(all_comments) < max_comments:
        endpoint = f"/graphql/query/?query_hash=bc3296d1ce80a24b1b6e40b1e72903f5&variables={json.dumps(variables)}"
        data = await make_instagram_request(endpoint)

        if not data or 'data' not in data or 'shortcode_media' not in data['data']:
            break

        comments_data = data['data']['shortcode_media']['edge_media_to_parent_comment']
        page_info = comments_data['page_info']

        for edge in comments_data['edges']:
            node = edge['node']
            all_comments.append({
                'comment_id': node['id'],
                'text': node['text'],
                'created_at': node['created_at'],
                'author_username': node['owner']['username'],
                'author_id': node['owner']['id'],
            })
            if len(all_comments) >= max_comments:
                break

        has_next_page = page_info['has_next_page']
        if has_next_page:
            variables['after'] = page_info['end_cursor']

    return all_comments
