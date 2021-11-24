# PY-NET
PY-NET is a cross-platform C&C server hosting program requiring zero third-party dependencies. Supporting both AES & TLS encrypted connections over TCP.

## Requirements
* [Python 3.8+](https://www.python.org/downloads/release/python-380/)
* (cryptography)

## Features
* Stable RCE & Reverse Shell
* Zero Third-party Dependencies
  * _Requires the cryptography library when using AES encryption_
* Cross-Platform
* Multiple Connection Types
  * Raw - Compression
  * Symmetric - Compression & AES Encryption
  * Asymmetric - TLS Encryption

## Implementation Features
* Secure TCP message implementation using a server side generated token for each message
* Fast TCP message transfer using bytearrays instead of strings
* Encryption of TCP headers when using AES encryption
* Specific encoding, encoding errors & language code support
* Support for shell & connection timeouts
* No HTTP overhead or dependency on the web

## Usage
* python host.py
* python bot.py

#### Generating Self-signed Keys
* python host.py --pubk_out [filepath] --privk_out [filepath]
  * _Requires openssl in your path variable_

#### Connecting to an AES Encrypted Host
* python bot.py --password [password] --salt [salt]

#### Connecting to an TLS Encrypted Host
* python bot.py --pubk_data "[public key string]"

## Commands
* exit
  * Exit the program

* cls
  * Clear the screen

* list
  * List all hosts & connected bots
  * This will show their ID used for specific interactions
  * This will also specify their session status

* listen (--hostname [hostname]) (--port [port]) (--password [password] & --salt [salt])
* listen (--hostname [hostname]) (--port [port]) (--pubk [public key filepath] & --privk [private key filepath])
  * --hostname & --port defaults to localhost & 38568
  * --password & --salt starts an AES encrypted host
  * --pubk & --privk starts an TLS encrypted host

* who --id [host or bot ID]
  * Specific address information of host or bot

* close --id [host or bot IDs separated by comma]
  * Closes connections of hosts or bots

* session --id [bot IDs separated by comma] (--remove)
  * --remove will remove the bot from the active session

## Session Commands
* ([command] | --filepath [filepath]) (--run) (--history)
  * A reverse shell for any command
  * --filepath sets the command with the file's content
  * --run executes the command as Python code instead
  * --history provides additional information of transferred data

---
_Please don't use PY-NET for illegal purposes_
