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

# API endpoints
block_api_url = 'https://sp-api.dappnode.io/memory/allblocks'
donation_api_url = 'https://sp-api.dappnode.io/memory/donations'

last_posted_tweet = None
last_posted_block = None 

def get_block_message(block):
    slot = block['slot']
    block_type = block['block_type']
    block_number = block['block']

    if 'reward_wei' in block:
        reward_wei = block['reward_wei']

        if block_type == 'wrongfeerecipient':
            address = block['withdrawal_address']
            amount = Web3.from_wei(int(reward_wei), 'ether')
            variation = random.choice(["🚨❌", "🚫❗️", "⛔", "❌💔", "⚠️🔒", "🔴🚫"])
            return f"{variation} BANNED FROM SMOOTH {variation} - {address} has been banned for sending {amount:.4f} ETH out of the pool"
        elif block_type == 'okpoolproposal':
            w3 = Web3()
            reward_eth = w3.from_wei(int(reward_wei), 'ether')
            variation = random.choice(["🚨", "🎉", "💰", "🔥", "🌟", "👑"]) 
            return f"{variation} NEW BLOCK IN SMOOTH {variation} - {reward_eth:.4f} ETH from a ☁️ Smooth Operator 😏 (Block #{block_number}, Slot #{slot})"
    else:
        print(f"Skipping tweet for block {block_number} (missing reward)")
        return None

def get_donation_message(donation):
    amount_eth = Web3.from_wei(int(donation['amount_wei']), 'ether')
    return f"🌟 NEW DONATION 🌟 - {amount_eth:.4f} ETH received from {donation['donor']} ({donation['message']})"

def post_tweet(api_url, message_type):
    global last_posted_tweet, last_posted_block 

    # Get the latest information from the API
    response = requests.get(api_url)
    
    # Check the API rate limit
    remaining_requests = int(response.headers.get('X-RateLimit-Remaining', 0))
    
    if remaining_requests <= 0:
        print(f"{message_type.capitalize()} API rate limit exceeded. Waiting until the next scheduled tweet.")
        return
    
    data = response.json()

    # Process the data based on the message type
    if message_type == 'block':
        block_number = data['block']

        # Check if the current block is the same as the last posted block
        if block_number == last_posted_block:
            print(f"Skipping {message_type} tweet (block {block_number} already posted)")
            return

        tweet_message = get_block_message(data)
    elif message_type == 'donation':
        tweet_message = get_donation_message(data)
    else:
        print(f"Invalid message type: {message_type}")
        return

    # Check if tweet_message is not None
    if tweet_message is not None:
        try:
            response = client.create_tweet(
                text=tweet_message
            )
            print(f"{message_type.capitalize()} tweet posted successfully! Tweet URL: https://twitter.com/user/status/{response.data['id']}")
            if message_type == 'block':
                print(f"Block Number: {block_number}\nSlot: {data['slot']}\nBlock_type: {data['block_type']}")
                last_posted_block = block_number
            last_posted_tweet = tweet_message
            print(f"Last Posted Tweet Updated: {last_posted_tweet}")
        except tweepy.errors.Forbidden as e:
            print(f"An error occurred: {e}")
        except tweepy.errors.TooManyRequests as e:
            print(f"Rate limit exceeded. Waiting and retrying...")
            time.sleep(60)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
    else:
        print(f"Skipping {message_type} tweet (duplicate content)")

# Schedule the tweet to run every two hours
schedule.every(2).hours.do(post_tweet, api_url=block_api_url, message_type='block')
schedule.every(2).hours.do(post_tweet, api_url=donation_api_url, message_type='donation')
print("Tweet scheduler set up.")

# Run the scheduler
while True:
    schedule.run_pending()
    time.sleep(1)
    print("Script is running...")
