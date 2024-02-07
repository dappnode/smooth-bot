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
donations_blocks_url = "https://sp-api.dappnode.io/memory/donations"

# By default, latest block twitted is 0
last_proposed_block = 0
last_wrong_fee_block = 0

# This  should be saved to data too
last_twit_index = 0

happy_emojis = ["🥳", "😊", "😄"]
sad_emojis = ["😔", "😞", "😢"]

happy_phrases = [
    "From a ☁️ Smooth Operator 😏",
    "Courtesy of a 🌤️ Smooth Operator 🤗",
    "Brought to you by a 🌬️ Smooth Operator 😎",
]

sad_phrases = [
    "Unfortunately, ",
    "Regrettably, ",
    "Sadly, ",
]

check_block_phrases = [
    "More info at:",
    "Link to the slot:",
    "Check the slot here:",
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

    # Local index variables for this function call
    local_emoji_index = last_twit_index
    local_phrase_index = last_twit_index
    local_ending_index = last_twit_index

    party_emoji = happy_emojis[local_emoji_index] if reward_eth > 0.1 else ""
    phrase = happy_phrases[local_phrase_index]
    ending = check_block_phrases[local_ending_index]
    slot_url = f"https://beaconcha.in/slot/{block_data['slot']}"

    tweet = (
        f"💰 NEW BLOCK IN SMOOTH 💰\n\n" 
        f"Reward: {reward_eth:.4f} ETH {party_emoji}\n\n" 
        f"{phrase}\n" 
        f"Proposer Validator Index: {block_data['validator_index']}\n\n" 
        f"{ending} {slot_url}"
    )
    try:
        client.create_tweet(text=tweet)
        logging.info(f"Successfully tweeted new proposed block: {tweet}")
    except tweepy.TweepyException as e:
        logging.error(f"Error while tweeting new wrong fee block: {e}")

    # Increment global index at the end of the function
    last_twit_index = (last_twit_index + 1) % len(happy_emojis) # Assuming all lists are the same length

def tweet_wrong_fee_block(block_data):
    global last_twit_index
    amount_eth = w3.from_wei(int(block_data['reward_wei']), 'ether')
    shortened_address = shorten_address(block_data['withdrawal_address'])

    # Local index variables for this function call
    local_emoji_index = last_twit_index
    local_phrase_index = last_twit_index
    local_ending_index = last_twit_index

    sad_emoji = sad_emojis[local_emoji_index]
    sad_phrase = sad_phrases[local_phrase_index]
    ending = check_block_phrases[local_ending_index]
    slot_url = f"https://beaconcha.in/slot/{block_data['slot']}"

    tweet = (
        f"⛔ BANNED FROM SMOOTH ⛔\n\n" 
        f"{sad_emoji} {sad_phrase}validator {shortened_address} has been banned for sending {amount_eth:.4f} ETH out of the pool {sad_emoji} \n\n"
        f"{ending} {slot_url}"
    )
    try:
        client.create_tweet(text=tweet)
        logging.info(f"Successfully tweeted new block: {tweet}")
    except tweepy.TweepyException as e:
        logging.error(f"Error while tweeting new block: {e}")

    # Increment global index at the end of the function
    last_twit_index = (last_twit_index + 1) % len(sad_emojis) # Assuming all lists are the same length

def fetch_donations_data(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Network error occurred when calling the Donations API: {e}")
        return None

def tweet_new_donation(donation_data):
    amount_eth = w3.from_wei(int(donation_data['amount_wei']), 'ether')
    donor_address = donation_data['donor_address']
    tweet = f"🎉 New Donation! 🎉\n\n" \
            f"Amount: {amount_eth:.4f} ETH\n" \
            f"Donor: {donor_address}\n\n" \
            f"Thank you for your support! 🙏"

    try:
        client.create_tweet(text=tweet)
        logging.info(f"Successfully tweeted new donation: {tweet}")
    except tweepy.TweepyException as e:
        logging.error(f"Error while tweeting new donation: {e}")

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

    # Fetching data from donation blocks
    try:
        logging.info("Fetching donation data from API.")
        donations_data = fetch_donations_data(donations_blocks_url)
        if donations_data:
            latest_donation = donations_data[-1]
            tweet_new_donation(latest_donation)
    except Exception as e:
        logging.error(f"Error while processing donations data: {e}")

    # Wait before next iteration
    logging.info("Waiting for next update cycle.")
    time.sleep(300)  # wait for 5 minutes
