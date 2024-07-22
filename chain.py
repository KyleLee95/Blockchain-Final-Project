import hashlib
import json
import requests
import numpy as np
from time import time
from urllib.parse import urlparse
from flask import Flask, jsonify, request
from uuid import uuid4
from cryptography.fernet import Fernet

# Generate a key for encryption
key = Fernet.generate_key()
cipher_suite = Fernet(key)


# Hashing function
def hash_data(data):
    return hashlib.sha256(data.encode()).hexdigest()


# Pseudonymization function
def pseudonymize_data(data):
    return str(uuid4())


# Data perturbation function
def perturb_data(value, noise_level=0.1):
    noise = np.random.normal(0, noise_level)
    return value + noise


def generalize_age(age):
    if age < 18:
        return "0-17"
    elif age < 30:
        return "18-29"
    elif age < 50:
        return "30-49"
    else:
        return "50+"


def encrypt_data(data):
    return cipher_suite.encrypt(data.encode()).decode()


# Anonymization pipeline
def anonymize_data(patient_data):
    anonymized_data = {
        "patient_id": hash_data(patient_data["patient_id"]),
        "age": generalize_age(patient_data["age"]),
        "weight": perturb_data(patient_data["weight"]),
        "gender": patient_data[
            "gender"
        ],  # Assuming gender is not highly sensitive in this context
        "encrypted_note": encrypt_data(patient_data["note"]),
    }
    return anonymized_data


class Blockchain:
    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.nodes = set()
        self.new_block(previous_hash="1", proof=100)

    def new_block(self, proof, previous_hash=None):
        block = {
            "index": len(self.chain) + 1,
            "timestamp": time(),
            "transactions": self.current_transactions,
            "proof": proof,
            "previous_hash": previous_hash or self.hash(self.chain[-1]),
        }
        self.current_transactions = []
        self.chain.append(block)
        return block

    def new_transaction(self, sender, recipient, amount):
        self.current_transactions.append(
            {
                "sender": sender,
                "recipient": recipient,
                "amount": amount,
            }
        )
        return self.last_block["index"] + 1

    @staticmethod
    def hash(block):
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        return self.chain[-1]

    def proof_of_work(self, last_proof):
        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1
        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        guess = f"{last_proof}{proof}".encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"

    def register_node(self, address):
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def valid_chain(self, chain):
        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            if block["previous_hash"] != self.hash(last_block):
                return False
            if not self.valid_proof(last_block["proof"], block["proof"]):
                return False
            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self):
        neighbours = self.nodes
        new_chain = None
        max_length = len(self.chain)

        for node in neighbours:
            response = requests.get(f"http://{node}/chain")

            if response.status_code == 200:
                length = response.json()["length"]
                chain = response.json()["chain"]

                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        if new_chain:
            self.chain = new_chain
            return True

        return False


app = Flask(__name__)
node_identifier = str(uuid4()).replace("-", "")
blockchain = Blockchain()


@app.route("/mine", methods=["GET"])
def mine():
    last_block = blockchain.last_block
    last_proof = last_block["proof"]
    proof = blockchain.proof_of_work(last_proof)
    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1,
    )
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        "message": "New Block Forged",
        "index": block["index"],
        "transactions": block["transactions"],
        "proof": block["proof"],
        "previous_hash": block["previous_hash"],
    }
    return jsonify(response), 200


@app.route("/transactions/new", methods=["POST"])
def new_transaction():
    values = request.get_json()
    required = ["sender", "recipient", "amount"]
    if not all(k in values for k in required):
        return "Missing values", 400

    index = blockchain.new_transaction(
        values["sender"], values["recipient"], values["amount"]
    )
    response = {"message": f"Transaction will be added to Block {index}"}
    return jsonify(response), 201


@app.route("/chain", methods=["GET"])
def full_chain():
    response = {
        "chain": blockchain.chain,
        "length": len(blockchain.chain),
    }
    return jsonify(response), 200


@app.route("/nodes/register", methods=["POST"])
def register_nodes():
    values = request.get_json()
    nodes = values.get("nodes")
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        "message": "New nodes have been added",
        "total_nodes": list(blockchain.nodes),
    }
    return jsonify(response), 201


@app.route("/nodes/resolve", methods=["GET"])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {"message": "Our chain was replaced", "new_chain": blockchain.chain}
    else:
        response = {"message": "Our chain is authoritative", "chain": blockchain.chain}

    return jsonify(response), 200


@app.route("/share_data", methods=["POST"])
def share_data():
    data = request.json

    # patient_id = data["patient_id"]
    # age = data["age"]
    # weight = data["weight"]
    # gender = data["gender"]
    # gender = data["note"]

    patient_data = {
        "patient_id": "patient_id_12345",
        "age": 25,
        "weight": 175,
        "gender": "male",
        "note": "Patient has a history of hypertension.",
    }

    anonymized_data = anonymize_data(patient_data)

    # Assuming a function to interact with the smart contract
    share_to_blockchain(anonymized_data)

    return jsonify({"message": "Data shared successfully"}), 200


def share_to_blockchain(patient_data):
    # Implement interaction with smart contract to share data
    pass


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument(
        "-p", "--port", default=5000, type=int, help="port to listen on"
    )
    args = parser.parse_args()
    port = args.port

    app.run(host="0.0.0.0", port=port)