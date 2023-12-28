import tweepy
import requests
import schedule
import time
from web3 import Web3
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

consumer_key = os.getenv("CONSUMER_KEY")
consumer_secret = os.getenv("CONSUMER_SECRET")
access_token = os.getenv("ACCESS_TOKEN")
access_token_secret = os.getenv("ACCESS_TOKEN_SECRET")

# Set up Twitter API authentication
client = tweepy.Client(
    consumer_key=consumer_key, consumer_secret=consumer_secret,
    access_token=access_token, access_token_secret=access_token_secret
)

# API endpoint for block information
block_api_url = 'https://sp-api.dappnode.io/memory/allblocks'

# Variable to store the last posted tweet content
last_posted_tweet = None

def post_tweet():
    global last_posted_tweet

    # Get the latest block information
    response = requests.get(block_api_url)
    blocks = response.json()  # Retrieve all blocks
    blocks.reverse()  # Reverse the order to get the latest block first

    # Get the latest block details
    latest_block = blocks[0]

    # Extract block details
    slot = latest_block['slot']
    block_type = latest_block['block_type']
    block_number = latest_block['block']
    validator_key = latest_block['validator_key']
    
    # Check if 'reward_wei' is present in the block information
    if 'reward_wei' in latest_block:
        reward_wei = latest_block['reward_wei']
        
        # Check the block type
        if block_type == 'wrongfeerecipient':
            # Post the tweet
            address = latest_block['withdrawal_address']
            amount = Web3.from_wei(int(latest_block['reward_wei']), 'ether')
            tweet_message = f"🚨❌ BANNED FROM SMOOTH ❌🚨 - {address} has been banned for sending {amount:.4f} ETH out of the pool."
        elif block_type == 'okpoolproposal':
            # Convert wei to ETH
            w3 = Web3()
            reward_eth = w3.from_wei(int(reward_wei), 'ether')

            # Create tweet message
            tweet_message = f"🚨 NEW BLOCK IN SMOOTH 🚨 - {reward_eth:.4f} ETH from a ☁️ Smooth Operator 😏 (Block #{block_number}, Slot #{slot})"
        
        # Check if the tweet message is different from the last posted tweet
        if tweet_message != last_posted_tweet:
            # Post the tweet
            try:
                response = client.create_tweet(
                    text=tweet_message
                )
                print(f"Tweet posted successfully! Tweet URL: https://twitter.com/user/status/{response.data['id']}")
                print(f"Block Number: {block_number}\nSlot: {slot}\nBlock_type: {block_type}")
                # Update the last posted tweet
                last_posted_tweet = tweet_message
            except tweepy.errors.Forbidden as e:
                print(f"An error occurred: {e}")
        else:
            print("Skipping tweet (duplicate content)")
    else:
        print(f"Skipping tweet for block {block_number} (missing reward)")

# Schedule the tweet to run every minute
schedule.every(1).minutes.do(post_tweet)

# Run the scheduler
while True:
    schedule.run_pending()
    time.sleep(1)
