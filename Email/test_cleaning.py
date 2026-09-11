from workspace.skills.outreach.auto_responder import clean_reply_text

def test_cleaning():
    dirty_email = """Hello,
I am interested in your project. Please tell me more.

On Wed, Apr 8, 2026 at 5:15 PM <tesseracapital@gmail.com> wrote:
> Hi Mayank,
> This is the old history that should be removed.
"""
    cleaned = clean_reply_text(dirty_email)
    print("--- Original ---")
    print(dirty_email)
    print("--- Cleaned ---")
    print(cleaned)
    print("--- End ---")
    
    assert "On Wed, Apr 8" not in cleaned
    assert "Interested in your project" in cleaned

if __name__ == "__main__":
    test_cleaning()
