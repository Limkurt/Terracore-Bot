import requests
import random
import string
import time
from colorama import Fore, Style, init

from threading import Thread
from beem.hive import Hive

init(autoreset=True)

red = Fore.RED
magenta = Fore.MAGENTA
green = Fore.GREEN
blue = Fore.BLUE
yellow = Fore.YELLOW
black = Fore.LIGHTBLACK_EX
default = Style.RESET_ALL


class app:
    class log:

        @staticmethod
        def time():
            return time.strftime("%H:%M:%S", time.localtime(time.time()))

        @staticmethod
        def print(message):
            print(f'{black}[{app.log.time()}]{default} {message}')


def read_accounts_file():
    with open('account/accounts.txt', 'r') as file:
        accounts = []
        for line in file.readlines():
            data = {
                'username': line.strip().split(':')[0],
                'active': line.strip().split(':')[1],
                'posting': line.strip().split(':')[2]
            }
            accounts.append(data)
        return accounts


def read_avoid_accounts_file():
    with open('account/avoid.txt', 'r') as file:
        return [line.strip() for line in file.readlines()]


def read_node_file():
    with open('config/node.txt', 'r') as file:
        return file.read()


def read_multiplier_file():
    with open('config/multiplier.txt', 'r') as file:
        return float(file.read())


def read_alt_usernames_file():
    with open('account/alts.txt', 'r') as file:
        return [line.strip() for line in file.readlines()]


def read_main_username_file():
    with open('account/main.txt', 'r') as file:
        return file.read()


def get_user_input():
    menu_options = ["1", "2", "3"]

    print("1 = Attack & Claim")
    print('2 = Transfer to Main Account')
    print('3 = Transfer to Alt Account')

    while True:
        user_input = input("Choose mode: ")

        if user_input in menu_options:
            return user_input
        else:
            print('- Please choose a valid option')


def get_player_data(username):
    while True:
        try:
            player_api = f'http://terracore.herokuapp.com/player/{username}'
            player_response = requests.get(player_api, timeout=1)
            if player_response.status_code == 200:
                return player_response.json()
        except:
            pass


def get_defender_data(attacker_damage):
    try:
        defender_api = f'https://terracore.herokuapp.com/battle?limit=20&offset=1&maxDefense={attacker_damage}'
        defender_response = requests.get(defender_api)
        if defender_response.status_code == 200:
            return defender_response.json()
    except:
        pass


already_attacked = []


def attack_claim(account):
    passwords = [account['active'], account['posting']]
    hive = Hive(keys=passwords, node=read_node_file())

    attacker_data = get_player_data(account['username'])
    defender_data = get_defender_data(attacker_data['stats']['damage'])

    if attacker_data is not None and defender_data is not None:
        for _ in range(attacker_data['attacks']):
            for defender in defender_data['players']:
                registration_time = defender['registrationTime'] // 1000 if 'registrationTime' in defender else 0
                last_battle = defender['lastBattle'] // 1000 if 'lastBattle' in defender else 0

                attacking_conditions = [
                    defender['scrap'] >= attacker_data['stats']['damage'] * read_multiplier_file(),
                    time.time() - registration_time > 86400,
                    time.time() - last_battle > 60,
                    defender['username'] not in read_avoid_accounts_file(),
                    defender['username'] not in already_attacked,
                    attacker_data['attacks'] > 0,
                    attacker_data['claims'] > 0
                ]

                if all(attacking_conditions):
                    try:
                        attack_hash = ''.join(random.choices(string.ascii_lowercase + string.digits, k=random.randint(20, 22)))
                        already_attacked.append(defender['username'])

                        data = {
                            'target': defender['username'],
                            'tx-hash': attack_hash
                        }

                        hive.custom_json("terracore_battle", data, required_auths=[account['username']])
                        app.log.print(f'{blue}{account["username"]}{default} attacked {magenta}{defender["username"]}{default} with {yellow}{defender["scrap"]:.6f}{default} SCRAP')
                        time.sleep(15)
                        break
                    except:
                        pass


    player_data = get_player_data(account['username'])

    claiming_conditions = [
        player_data['scrap'] >= player_data['stats']['defense'] * read_multiplier_file(),
        player_data['claims'] > 0
    ]

    if all(claiming_conditions):
        while True:
            try:
                claim_hash = ''.join(random.choices(string.ascii_lowercase + string.digits, k=random.randint(20, 22)))
                data = {
                    'amount': f"{player_data['scrap']:.6f}",
                    'tx-hash': claim_hash
                }
                hive.custom_json("terracore_claim", data, required_auths=[account['username']])
                app.log.print(f'{blue}{account["username"]}{default} claimed {yellow}{player_data["scrap"]:.6f}{default} SCRAP')
                time.sleep(15)
                break
            except:
                continue


def transfer_to_main(account):
    passwords = [account['active'], account['posting']]
    hive = Hive(keys=passwords, node=read_node_file())

    player_data = get_player_data(account['username'])

    if player_data is not None and player_data['hiveEngineScrap'] > 0:
        while True:
            try:
                data = {
                    "contractName": "tokens",
                    "contractAction": "transfer",
                    "contractPayload": {
                        "symbol": "SCRAP",
                        "to": read_main_username_file(),
                        "quantity": str(player_data['hiveEngineScrap']),
                        "memo": ""
                    }
                }

                hive.custom_json("ssc-mainnet-hive", data, required_auths=[account['username']])
                app.log.print(f'{blue}{account["username"]}{default} transferred {yellow}{player_data["hiveEngineScrap"]}{default} SCRAP to {magenta}{read_main_username_file()}{default}')
                break
            except:
                continue


def transfer_to_alts(amount, alt_username):
    for account in read_accounts_file():
        if account['username'] == read_main_username_file():
            passwords = [account['active'], account['posting']]
            hive = Hive(keys=passwords, node=read_node_file())

            while True:
                try:
                    data = {
                        "contractName": "tokens",
                        "contractAction": "transfer",
                        "contractPayload": {
                            "symbol": "SCRAP",
                            "to": alt_username,
                            "quantity": str(amount),
                            "memo": ""
                        }
                    }

                    hive.custom_json("ssc-mainnet-hive", data, required_auths=[account['username']])
                    app.log.print(f'{blue}{account["username"]}{default} transferred {yellow}{amount}{default} to {magenta}{alt_username}{default}')
                    break
                except:
                    continue
        break


def main():
    accounts = read_accounts_file()
    user_input = get_user_input()

    if user_input == '1':
        print()
        print('> Attack & Claim <')

        while True:
            threads = []
            thread_interval = 0
            for account in accounts:
                try:
                    time.sleep(thread_interval)
                    thread_interval += .05

                    thread = Thread(target=attack_claim, args=(account,))
                    threads.append(thread)
                    thread.start()
                except:
                    pass

            for thread in threads:
                thread.join()

            already_attacked.clear()
            time.sleep(60)

    if user_input == '2':
        print()
        print(f'> Transfer SCRAP from Alt Account to Main Account <')
        print()
        print(f'From: {", ".join(read_alt_usernames_file())}')
        print(f'To: {read_main_username_file()}')
        while True:
            print()
            confirmation = input(f'Confirm transfer (Y/N)?: ')
            if confirmation in ['Y', 'N'] and confirmation == 'Y':
                threads = []
                thread_interval = 0
                for account in accounts:
                    if account['username'] in read_alt_usernames_file():
                        try:
                            time.sleep(thread_interval)
                            thread_interval += .05

                            thread = Thread(target=transfer_to_main, args=(account,))
                            threads.append(thread)
                            thread.start()
                        except:
                            pass

                for thread in threads:
                    thread.join()

                print()
                any_keys = input('Enter any keys to close the window: ')
                if any_keys:
                    break
            elif confirmation in ['Y', 'N'] and confirmation == 'N':
                break
            else:
                print('- Please choose a valid option')

    if user_input == '3':
        print()
        print(f'> Transfer SCRAP from Main Account to Alt Account <')

        while True:
            amount = input('Amount to transfer: ')
            try:
                amount = float(amount)
                print()
                print(f'From: {read_main_username_file()}')
                print(f'To: {", ".join(read_alt_usernames_file())}')
                print(f'Amount to transfer: {amount} SCRAP')

                while True:
                    print()
                    confirmation = input(f'Confirm transfer (Y/N)?: ')
                    if confirmation in ['Y', 'N'] and confirmation == 'Y':
                        player_data = get_player_data(read_main_username_file())

                        if player_data is not None:
                            if player_data['hiveEngineScrap'] >= len(read_alt_usernames_file()) * amount:
                                threads = []
                                thread_interval = 0
                                for alt_username in read_alt_usernames_file():
                                    try:
                                        time.sleep(thread_interval)
                                        thread_interval += .05

                                        thread = Thread(target=transfer_to_alts, args=(amount, alt_username,))
                                        threads.append(thread)
                                        thread.start()
                                    except:
                                        pass

                                for thread in threads:
                                    thread.join()

                                print()
                                any_keys = input('Enter any keys to close the window: ')
                                if any_keys:
                                    break
                            else:
                                print(f'- {read_main_username_file()} only have {player_data["hiveEngineScrap"]} SCRAP. {len(read_alt_usernames_file()) * amount} SCRAP total amount to transfer.')
                                break
                    elif confirmation in ['Y', 'N'] and confirmation == 'N':
                        break
                    else:
                        print('- Please choose a valid option')
                break
            except:
                print('- Amount must be an integer or float number.')


if __name__ == '__main__':
    main()