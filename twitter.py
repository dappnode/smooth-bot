import os
import time
import requests
from web3 import Web3
import tweepy
from dotenv import load_dotenv
import json
import logging

LAST_BLOCKS_FILE = 'data/last_blocks.json'

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Twitter API credentials
consumer_key = os.getenv("CONSUMER_KEY")
consumer_secret = os.getenv("CONSUMER_SECRET")
access_token = os.getenv("ACCESS_TOKEN")
access_token_secret = os.getenv("ACCESS_TOKEN_SECRET")

client = tweepy.Client(
    consumer_key=consumer_key, consumer_secret=consumer_secret,
    access_token=access_token, access_token_secret=access_token_secret
)
logging.info("Twitter client initialized.")

# Web3 for converting Wei to Ether
w3 = Web3()

# Endpoints
proposed_blocks_url = "https://sp-api.dappnode.io/memory/proposedblocks"
wrong_fee_blocks_url = "https://sp-api.dappnode.io/memory/wrongfeeblocks"

# By default, latest block twitted is 0
last_proposed_block = 0
last_wrong_fee_block = 0

last_twit_index = 0

def get_next_item(items, last_index):
    next_index = (last_index + 1) % len(items)
    return items[next_index], next_index

happy_emojis = ["🥳", "😊", "😄"]
sad_emojis = ["😔", "😞", "😢"]

smooth_operator_phrases = [
    "From a ☁️ Smooth Operator 😏",
    "Courtesy of a 🌤️ Smooth Operator 🤗",
    "Brought to you by a 🌬️ Smooth Operator 😎",
]

def save_last_block(endpoint, block_number):
    data = {}
    try:
        with open(LAST_BLOCKS_FILE, 'r') as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        logging.warning("Could not load the last block data file; starting fresh.")


    data[endpoint] = block_number

    with open(LAST_BLOCKS_FILE, 'w') as file:
        json.dump(data, file)
    logging.info(f"Saved last block for {endpoint}: {block_number}")

def load_last_block(endpoint):
    try:
        with open(LAST_BLOCKS_FILE, 'r') as file:
            data = json.load(file)
            logging.info(f"Successfully Loaded last block for {endpoint}: {data.get(endpoint, 0)}")
            return data.get(endpoint, 0)
    except (FileNotFoundError, json.JSONDecodeError):
        logging.warning("Failed to load last block data, defaulting to 0.")
        return 0

# Load last blocks
last_proposed_block = load_last_block('proposed_blocks')
last_wrong_fee_block = load_last_block('wrong_fee_blocks')

def fetch_data(url):
    try:
        response = requests.get(url, timeout=10)  # 10 seconds timeout
        response.raise_for_status()  # This will raise an HTTPError if the HTTP request returned an unsuccessful status code
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Network error occurred when calling the Oracle: {e}")
        return None

def shorten_address(address):
    # Shorten the address to the first 6 and last 4 characters
    return address[:6] + '...' + address[-4:]

def tweet_new_block(block_data):
    global last_twit_index
    reward_eth = w3.from_wei(int(block_data['reward_wei']), 'ether')
    party_emoji, last_twit_index = get_next_item(happy_emojis, last_twit_index) if reward_eth > 0.1 else ""
    phrase, last_twit_index = get_next_item(smooth_operator_phrases, last_twit_index)
    slot_url = f"https://beaconcha.in/slot/{block_data['slot']}"
    
    tweet = (
        f"💰 NEW BLOCK IN SMOOTH 💰\n\n" 
        f"Reward: {reward_eth:.4f} ETH {party_emoji}\n\n" 
        f"{phrase}\n" 
        f"Proposer validator index: {block_data['validator_index']}\n" 
        f"{slot_url}"
    )
    try:
        client.create_tweet(text=tweet)
        logging.info(f"Successfully tweeted new proposed block: {tweet}")
    except tweepy.TweepyException as e:
        logging.error(f"Error while tweeting new wrong fee block: {e}")


def tweet_wrong_fee_block(block_data):
    global last_twit_index
    amount_eth = w3.from_wei(int(block_data['reward_wei']), 'ether')
    shortened_address = shorten_address(block_data['withdrawal_address'])
    sad_emoji, last_twit_index = get_next_item(sad_emojis, last_twit_index)
    slot_url = f"https://beaconcha.in/slot/{block_data['slot']}"

    tweet = (
        f"⛔ BANNED FROM SMOOTH ⛔\n\n" 
        f"{shortened_address} has been banned {sad_emoji}\n"
        f"For sending {amount_eth:.4f} ETH out of the pool\n"
        f"{slot_url}"
    )
    try:
        client.create_tweet(text=tweet)
        logging.info(f"Successfully tweeted new block: {tweet}")
    except tweepy.TweepyException as e:
        logging.error(f"Error while tweeting new block: {e}")

while True:
    # Fetching data from proposed blocks
    try:
        logging.info("Fetching proposed blocks data from Oracle.")
        proposed_blocks = fetch_data(proposed_blocks_url)
        if proposed_blocks and proposed_blocks[-1]['block'] != last_proposed_block:
            last_proposed_block = proposed_blocks[-1]['block']
            tweet_new_block(proposed_blocks[-1])
            save_last_block('proposed_blocks', last_proposed_block)
    except Exception as e:
        logging.error(f"Error while processing proposed blocks: {e}")

    # Fetching data from wrong fee blocks
    try:
        logging.info("Fetching wrong fee blocks data from Oracle.")
        wrong_fee_blocks = fetch_data(wrong_fee_blocks_url)
        if wrong_fee_blocks and wrong_fee_blocks[-1]['block'] != last_wrong_fee_block:
            last_wrong_fee_block = wrong_fee_blocks[-1]['block']
            tweet_wrong_fee_block(wrong_fee_blocks[-1])
            save_last_block('wrong_fee_blocks', last_wrong_fee_block)
    except Exception as e:
        logging.error(f"Error while processing wrong fee blocks: {e}")

    # Wait before next iteration
    logging.info("Waiting for next update cycle.")
    time.sleep(300)  # wait for 5 minutes
