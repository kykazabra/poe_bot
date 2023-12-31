import time
import os
import re
import keyboard
import json
import pickle
import pyautogui as pag


class BotPOE(object):
    def __init__(self):
        # Поменять путь к логам!
        self.log_path = r'Client (3).txt'
        self.data_path = r'data'
        self.logs = r'logs.txt'
        self.text_delay = 0.01
        self.action_delay = 0.02
        self.refresh_time = 1
        self.traders_in_lobby = 5
        # Включить инкремент мод
        self.increment_mode = False
        self.enable_price_check = True

        self.beg = 0
        self.trade_sender = ''
        self.text = ''
        self.traders = {}
        self.active_traders = []

        self.clear_logfile()
        self.load_data()
        self.calc_increment()
        self.body()

    def load_data(self):
        with open(self.data_path + r'\item_coords.json') as f:
            self.item_coords = json.load(f)

        with open(self.data_path + r'\inventory_coords.pickle', 'rb') as f:
            inventory_coords = pickle.load(f)
            self.inventory = {}
            for dct in inventory_coords:
                self.inventory[(dct['x'], dct['y'])] = False

        with open(self.data_path + r'\items_stacks.json') as f:
            self.items_stacks = json.load(f)

        with open(self.data_path + r'\trade_offer_coords.pickle', 'rb') as f:
            trade_offer_coords = pickle.load(f)
            self.trade_offer = {}
            for dct in trade_offer_coords:
                self.trade_offer[(dct['x'], dct['y'])] = False

        with open(self.data_path + r'\items_prices.json') as f:
            self.items_prices = json.load(f)

        with open(self.data_path + r'\accept_photo.pickle', 'rb') as f:
            self.accept_button_image = pickle.load(f)

        self.stash_coords = {'x': 1000, 'y': 400}

        self.accept_coords = {'x': 350, 'y': 840}

        self.logger('Data loaded!')

    def calc_increment(self):
        if self.increment_mode:
            with open(self.log_path, 'r', encoding="utf8") as f:
                text = f.read()
            self.beg = len(text)

    def clear_logfile(self):
        try:
            os.remove(self.logs)
        except:
            pass

    def logger(self, text):
        with open(self.logs, 'a', encoding="utf8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()) + '-' * 3 + text + '\n')

    def chat_print(self, text):
        keyboard.send('enter')
        keyboard.write(text, delay=self.text_delay)
        time.sleep(self.action_delay)
        keyboard.send('enter')

    def get_coords(self, item_name):
        item = self.item_coords[item_name]

        return item['x'] + 25, item['y'] + 25

    def get_items(self):
        items = re.findall(f"@From {self.trade_sender}: Hi, (?:I would|I'd) like to buy your ?(\d*) " \
                           "(.+) (?:listed for|for my) (\d*) (.+) in", self.text)

        self.items = list(items[-1])

        if not self.items[0].isdigit():
            self.items[0] = 1

        if not self.items[2].isdigit():
            self.items[2] = 1

        self.items[0], self.items[2] = int(self.items[0]), int(self.items[2])

        self.items = {'you_amount': self.items[0], 'you_item': self.items[1], 'him_amount': self.items[2],
                      'him_item': self.items[3]}

        self.logger(f"{self.trade_sender}'s items parsed from file: {self.items}")

    def read_logs(self):
        with open(self.log_path, 'r', encoding="utf8") as f:
            text = f.read()
        self.text = text[self.beg:]
        # self.logger('Refreshing logs')

    def check_offer(self, trader):
        items = re.findall(f"@From {trader}: Hi, (?:I would|I'd) like to buy your ?(\d*) " \
                           "(.+) (?:listed for|for my) (\d*) (.+) in", self.text)

        items = list(items[-1])

        if not items[0].isdigit():
            items[0] = 1

        if not items[2].isdigit():
            items[2] = 1

        items[0], items[2] = int(items[0]), int(items[2])

        items = {'you_amount': items[0], 'you_item': items[1], 'him_amount': items[2], 'him_item': items[3]}

        our_value = self.items_prices[items['you_item']]['price_buy']
        our_total_price = our_value * items['you_amount']

        him_total_price = items['him_amount']

        if our_total_price <= him_total_price:
            return True
        else:
            return False

    def add_traders(self):
        all_traders = re.findall(r"@From (.+): Hi, (?:I would|I'd) like to buy your ?\d* " \
                                 ".+ (?:listed for|for my) \d* .+ in", self.text)

        for trader in all_traders:
            if trader not in self.traders.keys():
                self.traders[trader] = {'status': 'Open', 'count': 1}

            elif all_traders.count(trader) > self.traders[trader]['count'] and self.traders[trader][
                'status'] == 'Closed':
                self.traders[trader]['status'] = 'Open'
                self.traders[trader]['count'] += 1

        for key, value in self.traders.items():
            if value['status'] == 'Open' and len(self.active_traders) < self.traders_in_lobby and \
                    key not in self.active_traders:
                self.active_traders.append(key)
                self.logger(f'Trader {key} added to active list')

                if self.enable_price_check:
                    if self.check_offer(key):
                        self.send_invite(key)

                    else:
                        self.active_traders.remove(key)
                        self.logger(f'Trader {key} removed from active list (bad offer)')
                        self.traders[key]['status'] = 'Closed'
                else:
                    self.send_invite(key)

    def remove_traders(self):
        for trader in self.active_traders:
            if len(re.findall(f'{trader} has left the area', self.text)) > self.traders[trader]['count'] - 1 \
                    and self.traders[trader]['status'] == 'Open':
                self.active_traders.remove(trader)
                self.traders[self.trade_sender]['status'] = 'Closed'
                self.logger(f'Trader {self.trade_sender} removed from active list (user left the area)')
                self.chat_print(f'/kick {self.trade_sender}')
                self.logger(f'{self.trade_sender} kicked from lobby')

    def join_check(self):
        count = 0
        while count != self.traders[self.trade_sender]['count']:
            count = len(re.findall(f'{self.trade_sender} has joined the area', self.text))

            time.sleep(self.refresh_time)
            self.read_logs()
            self.add_traders()
            self.logger(f'Waiting for {self.trade_sender} to join...')
        self.logger(f'{self.trade_sender} has joined the area')

    def trade_accept_check(self):
        while True:
            screenshot = pag.screenshot(region=(304, 821, 148, 32))

            if screenshot == self.accept_button_image:
                self.logger(f'{self.trade_sender} has accepted trade offer')
                break

            time.sleep(self.refresh_time)
            self.read_logs()
            self.add_traders()
            self.logger(f'Waiting for {self.trade_sender} to accept trade...')

    def send_invite(self, name):
        self.chat_print(f'/invite {name}')
        self.logger(f'{name} invited')

    def send_trade(self):
        self.chat_print(f'/tradewith {self.trade_sender}')
        self.logger(f'Trade sent to {self.trade_sender}')

    def stash_to_inventory(self):
        non_dragged = self.items['you_amount']

        while non_dragged > 0:
            if non_dragged > self.items_stacks[self.items['you_item']]:
                cur = self.items_stacks[self.items['you_item']]
            else:
                cur = non_dragged

            non_dragged -= cur

            pag.moveTo(*self.get_coords(self.items['you_item']))
            time.sleep(self.action_delay / 2)

            keyboard.press('shift')
            pag.click()
            keyboard.release('shift')

            time.sleep(self.action_delay / 2)
            if 10 <= cur <= 99:
                keyboard.send(str(cur)[0])
                keyboard.send(str(cur)[1])
            else:
                keyboard.send(str(cur))

            keyboard.send('enter')

            time.sleep(self.action_delay / 2)
            pag.mouseDown(button='left')

            for key, value in self.inventory.items():
                if not value:
                    pag.moveTo(key[0] + 25, key[1] + 25)
                    self.inventory[key] = True
                    break

            pag.mouseUp(button='left')
            time.sleep(self.action_delay / 2)

    def inventory_to_trade(self):
        for key, value in self.inventory.items():
            if value:
                time.sleep(self.action_delay / 2)
                pag.moveTo(key[0] + 25, key[1] + 25)
                keyboard.press('ctrl')
                pag.click()
                keyboard.release('ctrl')
                self.inventory[key] = False

    def trade_offer_to_inventory(self):
        for key, value in self.trade_offer.items():
            time.sleep(self.action_delay / 40)
            pag.moveTo(key[0] + 25, key[1] + 25)

    def push_accept(self):
        pag.moveTo(self.accept_coords['x'], self.accept_coords['y'])
        pag.click()

    def open_stash(self):
        pag.moveTo(self.stash_coords['x'], self.stash_coords['y'])
        pag.click()

    def inventory_to_stash(self):
        keyboard.press('ctrl')
        for key, value in self.inventory.items():
            time.sleep(self.action_delay / 80)
            pag.moveTo(key[0] + 25, key[1] + 25)
            pag.click()

        keyboard.release('ctrl')

    def close_trader(self):
        self.active_traders.remove(self.trade_sender)
        self.traders[self.trade_sender]['status'] = 'Closed'
        self.logger(f'Trader {self.trade_sender} removed from active list (trade finished successfully)')
        self.chat_print(f'/kick {self.trade_sender}')
        self.logger(f'{self.trade_sender} kicked from lobby')

    def body(self):
        time.sleep(5)

        while True:
            self.read_logs()
            self.add_traders()

            if self.active_traders:
                self.trade_sender = self.active_traders[0]
                self.logger(f'Current trader: {self.trade_sender}')

                self.get_items()

                self.join_check()

                self.stash_to_inventory()

                self.send_trade()

                self.trade_accept_check()

                self.inventory_to_trade()

                time.sleep(3)

                self.trade_offer_to_inventory()

                time.sleep(self.action_delay)

                self.push_accept()

                time.sleep(self.action_delay)

                self.open_stash()

                time.sleep(self.action_delay)

                self.inventory_to_stash()

                self.close_trader()

            else:
                time.sleep(self.refresh_time)


BotPOE();
