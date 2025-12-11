import instaloader
import os

def scrape_instagram_hashtag(hashtag, max_comments=20):
    try:
        L = instaloader.Instaloader()

        # Sessionid bilan login
        sessionid = os.environ.get('INSTAGRAM_SESSIONID')

        if sessionid:
            L.context._session.cookies.set('sessionid', sessionid, domain='instagram.com')
            print("✅ Using sessionid")
        else:
            print("❌ No sessionid found")
            return []

        # Hashtag scraping
        hashtag_obj = instaloader.Hashtag.from_name(L.context, hashtag)
        comments_data = []

        post_count = 0
        for post in hashtag_obj.get_posts():
            if post_count >= 5:
                break
            post_count += 1

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
            if len(comments_data) >= max_comments:
                break

        print(f"✅ Total comments collected: {len(comments_data)}")
        return comments_data

    except Exception as e:
        print(f"Error: {e}")
        return []
