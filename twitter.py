import tweepy
import requests
import schedule
import time
from web3 import Web3
from dotenv import load_dotenv
import os
import random

load_dotenv()

consumer_key = os.getenv("CONSUMER_KEY")
consumer_secret = os.getenv("CONSUMER_SECRET")
access_token = os.getenv("ACCESS_TOKEN")
access_token_secret = os.getenv("ACCESS_TOKEN_SECRET")

# Check if any of the API credentials are missing
if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
    raise ValueError("One or more Twitter API credentials are missing. Please check your .env file.")
else:
    print("Twitter API credentials found.")

client = tweepy.Client(
    consumer_key=consumer_key, consumer_secret=consumer_secret,
    access_token=access_token, access_token_secret=access_token_secret
)
print("Twitter client initialized.")

# Separate API endpoints for block information
proposed_blocks_api_url = 'https://sp-api.dappnode.io/memory/proposedblocks'
wrong_fee_blocks_api_url = 'https://sp-api.dappnode.io/memory/wrongfeeblocks'

last_posted_tweet = None
last_posted_block = None

def get_block_message(block):
    slot = block['slot']
    block_type = block['block_type']
    block_number = block['block']
    validator_key = block['validator_key']

    # Check if 'reward_wei' is present in the block information
    if 'reward_wei' in block:
        reward_wei = block['reward_wei']

        # Check the block type
        if block_type == 'wrongfeerecipient':
            # Post the tweet with some variation
            address = block['withdrawal_address']
            amount = Web3.from_wei(int(block['reward_wei']), 'ether')
            variation = random.choice(["🚨❌", "🚫❗️", "⛔", "❌💔", "⚠️🔒", "🔴🚫"])
            return f"{variation} BANNED FROM SMOOTH {variation} - {address} has been banned for sending {amount:.4f} ETH out of the pool"
        elif block_type == 'okpoolproposal':
            # Convert wei to ETH
            w3 = Web3()
            reward_eth = w3.from_wei(int(reward_wei), 'ether')

            # Create tweet message with some variation
            variation = random.choice(["🚨", "🎉", "💰", "🔥", "🌟", "👑"]) 
            return f"{variation} NEW BLOCK IN SMOOTH {variation} - {reward_eth:.4f} ETH from a ☁️ Smooth Operator 😏 (Block #{block_number}, Slot #{slot})"
    else:
        print(f"Skipping tweet for block {block_number} (missing reward)")
        return None

# Store the IDs of the last posted tweets
last_posted_tweet_ids = set()

def post_tweet(api_url):
    global last_posted_tweet, last_posted_block, last_posted_tweet_ids

    # Get the latest block information
    response = requests.get(api_url)
    blocks = response.json()
    latest_block = blocks[-1]  # Assuming the latest block is at the end of the list

    block_number = latest_block['block']

    # Check if the current block is the same as the last posted block
    if block_number == last_posted_block:
        print(f"Skipping tweet (block {block_number} already posted)")
        return

    tweet_message = get_block_message(latest_block)
    
     # Print the tweet_message and last_posted_tweet for debugging
    print(f"Tweet Message: {tweet_message}")
    print(f"Last Posted Tweet: {last_posted_tweet}")

    # Check if the tweet_message is not None and is different from the last posted tweet
    if tweet_message is not None and tweet_message != last_posted_tweet:
        try:
            response = client.create_tweet(
                text=tweet_message
            )
            tweet_id = response.data['id']
            print(f"Tweet posted successfully! Tweet URL: https://twitter.com/user/status/{tweet_id}")
            print(f"Block Number: {block_number}\nSlot: {latest_block['slot']}\nBlock_type: {latest_block['block_type']}")

            # Update last posted information
            last_posted_tweet = tweet_message
            last_posted_block = block_number
            last_posted_tweet_ids.add(tweet_id)
            print(f"Last Posted Tweet Updated: {last_posted_tweet}")
        except tweepy.errors.Forbidden as e:
            print(f"An error occurred: {e}")
        except tweepy.errors.TooManyRequests as e:
            print(f"Rate limit exceeded. Waiting and retrying...")
            time.sleep(60)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
    else:
        print("Skipping tweet (duplicate content)")

# Schedule the tweet to run every four hours only if there are new blocks
schedule.every(6).hours.do(lambda: post_tweet(proposed_blocks_api_url))
schedule.every(6).hours.do(lambda: post_tweet(wrong_fee_blocks_api_url))
print("Tweet scheduler set up.")

# Run the scheduler
while True:
    schedule.run_pending()
    time.sleep(1)
    print("Script is running...")
