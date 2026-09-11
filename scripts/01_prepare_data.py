"""
STEP 1 of the pipeline: turn the raw Twitter dump into clean (customer tweet -> Apple reply) pairs.

Input : data/twcs.csv   (Kaggle: thoughtvector/customer-support-on-twitter, ~2.8M tweets)
Output: data/apple_pairs.csv                 every pair we found (NOT committed, too big)
        sample_data/apple_pairs_sample.csv   5,000 random pairs (committed, so anyone can reproduce)

How the raw data links together:
  every row is one tweet.  If tweet B is a reply to tweet A, then B.in_response_to_tweet_id == A.tweet_id
  So "find Apple's replies, then look up the tweet each one was replying to" gives us our pairs.

Run:  python scripts/01_prepare_data.py
"""
import re
from pathlib import Path

import pandas as pd

BRAND = "AppleSupport"
RAW_FILE = Path("data/twcs.csv")
FULL_OUT = Path("data/apple_pairs.csv")
SAMPLE_OUT = Path("sample_data/apple_pairs_sample.csv")
SAMPLE_SIZE = 5000
SEED = 42              # fixed seed = same "random" sample every time
CHUNK_ROWS = 250_000   # read the 500 MB file in pieces so a laptop doesn't run out of memory

TIME_FORMAT = "%a %b %d %H:%M:%S %z %Y"   # looks like: "Tue Oct 31 22:10:47 +0000 2017"


# ---------------------------------------------------------------- cleaning helpers
def clean_text(text: str) -> str:
    """Remove the @handles at the start, hide links and customer ids, squash extra spaces."""
    text = re.sub(r"^(\s*@\w+)+", "", text)          # "@AppleSupport @115712 my phone..." -> "my phone..."
    text = re.sub(r"https?://\S+", "<URL>", text)    # links are useless to the model
    text = re.sub(r"@\d+", "@user", text)            # customers are numbers in this dataset
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return re.sub(r"\s+", " ", text).strip()


def mostly_english_letters(text: str) -> bool:
    """Cheap language filter: at least 90% of the letters are plain a-z."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False
    return sum(c.isascii() for c in letters) / len(letters) >= 0.9


# ---------------------------------------------------------------- pass 1: Apple's replies
def load_brand_replies() -> pd.DataFrame:
    parts = []
    cols = ["tweet_id", "author_id", "created_at", "text", "in_response_to_tweet_id"]
    for chunk in pd.read_csv(RAW_FILE, usecols=cols, chunksize=CHUNK_ROWS):
        mine = chunk[(chunk["author_id"] == BRAND) & chunk["in_response_to_tweet_id"].notna()]
        parts.append(mine)
    replies = pd.concat(parts, ignore_index=True)
    replies["in_response_to_tweet_id"] = replies["in_response_to_tweet_id"].astype("int64")
    return replies.rename(columns={
        "tweet_id": "reply_tweet_id",
        "created_at": "reply_created_at",
        "text": "reply_text_raw",
        "in_response_to_tweet_id": "customer_tweet_id",
    }).drop(columns=["author_id"])


# ---------------------------------------------------------------- pass 2: the customer tweets they answered
def load_customer_tweets(wanted_ids: set) -> pd.DataFrame:
    parts = []
    cols = ["tweet_id", "author_id", "inbound", "created_at", "text", "in_response_to_tweet_id"]
    for chunk in pd.read_csv(RAW_FILE, usecols=cols, chunksize=CHUNK_ROWS):
        hit = chunk[chunk["tweet_id"].isin(wanted_ids) & (chunk["inbound"] == True)]  # noqa: E712
        parts.append(hit)
    customers = pd.concat(parts, ignore_index=True)
    # first contact = the customer was NOT replying to anything (they started the conversation)
    customers["is_first_contact"] = customers["in_response_to_tweet_id"].isna()
    return customers.rename(columns={
        "tweet_id": "customer_tweet_id",
        "author_id": "customer_id",
        "created_at": "customer_created_at",
        "text": "customer_text_raw",
    }).drop(columns=["inbound", "in_response_to_tweet_id"])


def main():
    if not RAW_FILE.exists():
        raise SystemExit(f"Can't find {RAW_FILE}. Download twcs.csv from Kaggle into the data/ folder first.")

    print(f"Pass 1/2: finding every @{BRAND} reply ... (takes ~1 minute)")
    replies = load_brand_replies()
    print(f"   found {len(replies):,} replies")

    print("Pass 2/2: finding the customer tweets they replied to ...")
    customers = load_customer_tweets(set(replies["customer_tweet_id"]))
    print(f"   found {len(customers):,} customer tweets")

    pairs = replies.merge(customers, on="customer_tweet_id", how="inner")

    # times -> real datetimes so we can sort and measure response speed
    for col in ["reply_created_at", "customer_created_at"]:
        pairs[col] = pd.to_datetime(pairs[col], format=TIME_FORMAT, utc=True)

    # a customer tweet can get 2+ replies from Apple: keep only the FIRST one
    pairs = pairs.sort_values("reply_created_at").drop_duplicates("customer_tweet_id", keep="first")

    # keep only conversation starters: that is what an incoming-message agent sees
    counts = {"all pairs": len(pairs)}
    pairs = pairs[pairs["is_first_contact"]]
    counts["first-contact only"] = len(pairs)

    pairs["customer_text"] = pairs["customer_text_raw"].map(clean_text)
    pairs["reply_text"] = pairs["reply_text_raw"].map(clean_text)

    pairs = pairs[pairs["customer_text"].str.len() >= 10]
    counts["at least 10 characters"] = len(pairs)
    pairs = pairs[pairs["customer_text"].map(mostly_english_letters)]
    counts["mostly English"] = len(pairs)
    pairs = pairs.drop_duplicates("customer_text")
    counts["no duplicate texts"] = len(pairs)

    pairs["response_minutes"] = (
        (pairs["reply_created_at"] - pairs["customer_created_at"]).dt.total_seconds() / 60
    ).round(1)
    pairs["reply_asks_dm"] = pairs["reply_text"].str.contains(r"\bDM\b|direct message", case=False, regex=True)

    keep = ["customer_tweet_id", "customer_id", "customer_created_at", "customer_text", "customer_text_raw",
            "reply_tweet_id", "reply_created_at", "reply_text", "reply_text_raw",
            "response_minutes", "reply_asks_dm"]
    pairs = pairs[keep].reset_index(drop=True)

    FULL_OUT.parent.mkdir(exist_ok=True)
    SAMPLE_OUT.parent.mkdir(exist_ok=True)
    pairs.to_csv(FULL_OUT, index=False)
    sample = pairs.sample(n=min(SAMPLE_SIZE, len(pairs)), random_state=SEED)
    sample.to_csv(SAMPLE_OUT, index=False)

    # ---------------------------------------------------------------- quick report card
    print("\nHow many pairs survived each filter:")
    for name, n in counts.items():
        print(f"   {name:<25} {n:>8,}")
    print(f"\nSaved {len(pairs):,} pairs  -> {FULL_OUT}")
    print(f"Saved {len(sample):,} sample -> {SAMPLE_OUT}")
    print(f"\nReplies that ask the customer to DM : {pairs['reply_asks_dm'].mean():.1%}")
    print(f"Median time to first reply           : {pairs['response_minutes'].median():.0f} minutes")
    print(f"Median customer tweet length         : {pairs['customer_text'].str.len().median():.0f} characters")

    print("\n5 random examples:")
    for _, row in sample.head(5).iterrows():
        print(f"\n   CUSTOMER: {row['customer_text'][:150]}")
        print(f"   APPLE   : {row['reply_text'][:150]}")


if __name__ == "__main__":
    main()