import tweepy
import requests
import schedule
import time
from web3 import Web3
from dotenv import load_dotenv
import os
import random  # Import the random module

load_dotenv()

consumer_key = os.getenv("CONSUMER_KEY")
consumer_secret = os.getenv("CONSUMER_SECRET")
access_token = os.getenv("ACCESS_TOKEN")
access_token_secret = os.getenv("ACCESS_TOKEN_SECRET")

client = tweepy.Client(
    consumer_key=consumer_key, consumer_secret=consumer_secret,
    access_token=access_token, access_token_secret=access_token_secret
)

# API endpoint for block information
block_api_url = 'https://sp-api.dappnode.io/memory/allblocks'

# Initialize last_posted_tweet with an empty string
last_posted_tweet = ''

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
            variation = random.choice(["🚨❌", "🚫❗️", "⛔"])  # Add some random variation
            return f"{variation} BANNED FROM SMOOTH {variation} - {address} has been banned for sending {amount:.4f} ETH out of the pool"
        elif block_type == 'okpoolproposal':
            # Convert wei to ETH
            w3 = Web3()
            reward_eth = w3.from_wei(int(reward_wei), 'ether')

            # Create tweet message with some variation
            variation = random.choice(["🚨", "🎉", "💰"])  # Add some random variation
            return f"{variation} NEW BLOCK IN SMOOTH {variation} - {reward_eth:.4f} ETH from a ☁️ Smooth Operator 😏 (Block #{block_number}, Slot #{slot})"
    else:
        print(f"Skipping tweet for block {block_number} (missing reward)")
        return None

def post_tweet():
    global last_posted_tweet

    # Get the latest 6 block information
    response = requests.get(block_api_url)
    blocks = response.json()
    blocks.reverse()
    latest_blocks = blocks[:6]

    # Iterate over the latest 6 blocks
    for block in latest_blocks:
        tweet_message = get_block_message(block)

        # Check if tweet_message is not None and if it's different from the last posted tweet
        if tweet_message is not None and tweet_message.strip() != last_posted_tweet.strip():
            # Post the tweet with backoff and retry
            try:
                response = client.create_tweet(
                    text=tweet_message
                )
                print(f"Tweet posted successfully! Tweet URL: https://twitter.com/user/status/{response.data['id']}")
                print(f"Block Number: {block['block']}\nSlot: {block['slot']}\nBlock_type: {block['block_type']}")
                # Update the last posted tweet
                last_posted_tweet = tweet_message
                print(f"Last Posted Tweet Updated: {last_posted_tweet}")
            except tweepy.errors.Forbidden as e:
                print(f"An error occurred: {e}")
            except tweepy.errors.TooManyRequests as e:
                print(f"Rate limit exceeded. Waiting and retrying...")
                time.sleep(60)  # Wait for 60 seconds before retrying
        else:
            print("Skipping tweet (duplicate content)")

# Schedule the tweet to run every minute
schedule.every(1).minutes.do(post_tweet)

# Run the scheduler
while True:
    schedule.run_pending()
    time.sleep(1)
