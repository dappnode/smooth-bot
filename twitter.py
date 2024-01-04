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

# API endpoint for block information
block_api_url = 'https://sp-api.dappnode.io/memory/allblocks'

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

def post_tweet():
    global last_posted_tweet, last_posted_block 

    # Get the latest 6 block information
    response = requests.get(block_api_url)
    blocks = response.json()
    blocks.reverse()
    latest_blocks = blocks[:6]

    # Iterate over the latest 6 blocks
    for block in latest_blocks:
        block_number = block['block']

        # Check if the current block is the same as the last posted block
        if block_number == last_posted_block:
            print(f"Skipping tweet (block {block_number} already posted)")
            continue

        tweet_message = get_block_message(block)

        # Check if tweet_message is not None
        if tweet_message is not None:
            try:
                response = client.create_tweet(
                    text=tweet_message
                )
                print(f"Tweet posted successfully! Tweet URL: https://twitter.com/user/status/{response.data['id']}")
                print(f"Block Number: {block_number}\nSlot: {block['slot']}\nBlock_type: {block['block_type']}")
                last_posted_tweet = tweet_message
                last_posted_block = block_number
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

# Schedule the tweet to run every minute
schedule.every(1).minutes.do(post_tweet)
print("Tweet scheduler set up.")

# Run the scheduler
while True:
    schedule.run_pending()
    time.sleep(1)
    print("Script is running...")
