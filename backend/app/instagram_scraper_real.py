import instaloader
import os
from flask import current_app

def scrape_instagram_hashtag(hashtag, max_comments=20):
    """
    Instaloader bilan Instagram hashtag'dan comments olish
    """
    try:
        L = instaloader.Instaloader()

        # Instagram login (muhim!)
        username = os.environ.get('INSTAGRAM_USERNAME')
        password = os.environ.get('INSTAGRAM_PASSWORD')

        if not username or not password:
            print("⚠️ Instagram credentials not found!")
            return []

        try:
            L.login(username, password)
            print(f"✅ Logged in as {username}")
        except Exception as e:
            print(f"❌ Login failed: {e}")
            return []

        # Hashtag'dan postlar olish
        hashtag_obj = instaloader.Hashtag.from_name(L.context, hashtag)
        comments_data = []

        print(f"🔍 Searching #{hashtag}...")

        post_count = 0
        for post in hashtag_obj.get_posts():
            if post_count >= 5:  # Faqat 5 ta post
                break

            post_count += 1
            print(f"📝 Post {post_count}: {post.shortcode}")

            # Comments olish
            try:
                for comment in post.get_comments():
                    if len(comments_data) >= max_comments:
                        break

                    comments_data.append({
                        'author_username': comment.owner.username,
                        'text': comment.text,
                        'created_at': int(comment.created_at_utc.timestamp()),
                        'comment_id': str(comment.id),
                        'author_id': str(comment.owner.userid)
                    })

                    print(f"  💬 @{comment.owner.username}: {comment.text[:50]}...")

                    if len(comments_data) >= max_comments:
                        break
            except Exception as e:
                print(f"  ⚠️ Error getting comments: {e}")
                continue

        print(f"✅ Total comments collected: {len(comments_data)}")
        return comments_data

    except Exception as e:
        print(f"❌ Scraping error: {e}")
        return []
