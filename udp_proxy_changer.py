"""
Bulk WebRTC Changer for AdsPower
Test values on a single profile, then bulk change a folder.
"""

import tkinter as tk
from tkinter import messagebox
import threading
import json
import time

try:
    import urllib.request
    import urllib.error
except ImportError:
    pass

API_BASE = "http://127.0.0.1:50325"


def api_get(path):
    try:
        url = API_BASE + path
        req = urllib.request.Request(url, method='GET')
        req.add_header('Content-Type', 'application/json')
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {'code': -1, 'msg': str(e)}


def api_post(path, data=None):
    try:
        url = API_BASE + path
        body = json.dumps(data or {}).encode('utf-8')
        req = urllib.request.Request(url, data=body, method='POST')
        req.add_header('Content-Type', 'application/json')
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {'code': -1, 'msg': str(e)}


def find_profile(serial):
    for attempt in range(3):
        resp = api_get(f'/api/v1/user/list?serial_number={serial}')
        if resp.get('code') == 0:
            profiles = resp.get('data', {}).get('list', [])
            if profiles:
                return profiles[0].get('user_id', '')
        if 'Too many request' in resp.get('msg', ''):
            time.sleep(2)
        else:
            break
    return ''


class WebRTCChangerApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('AdsPower WebRTC Changer')
        self.root.geometry('550x550')
        self.root.resizable(True, True)
        self.root.configure(bg='#1a1a2e')
        self.running = False
        self.groups = {}

        self._build_ui()

    def _log(self, msg):
        ts = time.strftime('%H:%M:%S')
        line = f'[{ts}] {msg}'
        print(line)
        self.log_text.configure(state='normal')
        self.log_text.insert('end', line + '\n')
        self.log_text.see('end')
        self.log_text.configure(state='disabled')

    def _build_ui(self):
        tk.Label(self.root, text='WEBRTC CHANGER',
                 font=('Segoe UI', 16, 'bold'),
                 fg='#e94560', bg='#1a1a2e').pack(pady=(10, 3))

        # Test section
        tf = tk.LabelFrame(self.root, text=' Test Single Profile ',
                 font=('Segoe UI', 9, 'bold'),
                 fg='#FFD700', bg='#1a1a2e', padx=10, pady=5)
        tf.pack(fill='x', padx=15, pady=(5, 5))

        row1 = tk.Frame(tf, bg='#1a1a2e')
        row1.pack(fill='x', pady=2)
        tk.Label(row1, text='Profile #:', font=('Segoe UI', 10),
                 fg='#fff', bg='#1a1a2e').pack(side='left')
        self.serial_entry = tk.Entry(row1, font=('Consolas', 12), width=10,
                                      bg='#0f3460', fg='#FFD700',
                                      insertbackground='#FFD700', border=1)
        self.serial_entry.pack(side='left', padx=(5, 10))

        values = ['forward', 'proxy', 'local', 'disabled', 'disable_udp']
        for val in values:
            tk.Button(row1, text=val, font=('Segoe UI', 8),
                      fg='#fff', bg='#0f3460', border=0, padx=6, pady=2,
                      cursor='hand2',
                      command=lambda v=val: self._test_value(v)).pack(side='left', padx=2)

        # Bulk section
        bf = tk.LabelFrame(self.root, text=' Bulk Change Folder ',
                 font=('Segoe UI', 9, 'bold'),
                 fg='#FFD700', bg='#1a1a2e', padx=10, pady=5)
        bf.pack(fill='x', padx=15, pady=(5, 5))

        row2 = tk.Frame(bf, bg='#1a1a2e')
        row2.pack(fill='x', pady=2)

        tk.Label(row2, text='Folder:', font=('Segoe UI', 10),
                 fg='#fff', bg='#1a1a2e').pack(side='left')
        self.group_var = tk.StringVar(value='-- Click Load --')
        self.group_menu = tk.OptionMenu(row2, self.group_var, '-- Click Load --')
        self.group_menu.configure(font=('Segoe UI', 9), fg='#fff',
                                   bg='#0f3460', activebackground='#16213e',
                                   highlightthickness=0, width=25, anchor='w')
        self.group_menu.pack(side='left', padx=(5, 5))
        tk.Button(row2, text='Load', font=('Segoe UI', 8),
                  fg='#fff', bg='#0f3460', border=0, padx=8, pady=2,
                  cursor='hand2', command=self._load_groups).pack(side='left')

        row3 = tk.Frame(bf, bg='#1a1a2e')
        row3.pack(fill='x', pady=(5, 2))

        tk.Label(row3, text='Value:', font=('Segoe UI', 10),
                 fg='#fff', bg='#1a1a2e').pack(side='left')
        self.bulk_var = tk.StringVar(value='proxy')
        bulk_menu = tk.OptionMenu(row3, self.bulk_var, *values)
        bulk_menu.configure(font=('Consolas', 11), fg='#FFD700',
                             bg='#0f3460', activebackground='#16213e',
                             highlightthickness=0, width=12)
        bulk_menu.pack(side='left', padx=(5, 10))

        self.start_btn = tk.Button(row3, text='CHANGE ALL',
                  font=('Segoe UI', 10, 'bold'),
                  fg='#fff', bg='#e94560', activebackground='#ff6b8a',
                  border=0, padx=15, pady=4,
                  cursor='hand2', command=self._start_bulk)
        self.start_btn.pack(side='left')

        self.progress_label = tk.Label(self.root, text='',
                 font=('Segoe UI', 10, 'bold'),
                 fg='#44dd44', bg='#1a1a2e')
        self.progress_label.pack(pady=2)

        lf = tk.Frame(self.root, bg='#1a1a2e')
        lf.pack(fill='both', expand=True, padx=15, pady=(2, 10))
        tk.Label(lf, text='Log', font=('Segoe UI', 8), fg='#8888aa', bg='#1a1a2e').pack(anchor='w')
        self.log_text = tk.Text(lf, font=('Consolas', 8), bg='#0a0a1a', fg='#44dd44',
                                insertbackground='#44dd44', border=0, wrap='word', state='disabled')
        self.log_text.pack(fill='both', expand=True, pady=2)

        self._log('Enter a profile # and click a value to test.')
        self._log('Values: forward, proxy, local, disabled, disable_udp')
        self._log('Check AdsPower after each click to see which = Proxy UDP')

    def _test_value(self, val):
        serial = self.serial_entry.get().strip()
        if not serial:
            self._log('Enter a profile number first!')
            return

        def do_test():
            self.root.after(0, lambda: self._log(
                f'Finding profile #{serial}...'))
            uid = find_profile(serial)
            if not uid:
                self.root.after(0, lambda: self._log(
                    f'Profile #{serial} not found'))
                return

            r = api_post('/api/v1/user/update', {
                'user_id': uid,
                'fingerprint_config': {'webrtc': val}
            })
            code = r.get('code', -1)
            msg = r.get('msg', '')
            self.root.after(0, lambda: self._log(
                f'SET #{serial} webrtc="{val}" => code={code} msg={msg}'))
            self.root.after(0, lambda: self._log(
                f'>> Check profile #{serial} in AdsPower now'))

        threading.Thread(target=do_test, daemon=True).start()

    def _load_groups(self):
        def do_load():
            self.groups = {}
            self.root.after(0, lambda: self._log('Loading folders...'))

            page = 1
            while True:
                resp = None
                for attempt in range(3):
                    resp = api_get(f'/api/v1/group/list?page={page}&page_size=100')
                    if resp.get('code') == 0:
                        break
                    if 'Too many request' in resp.get('msg', ''):
                        time.sleep(1.5)
                    else:
                        break

                if resp.get('code') != 0:
                    break
                grp_list = resp.get('data', {}).get('list', [])
                if isinstance(resp.get('data'), list):
                    grp_list = resp['data']
                if not grp_list:
                    break
                for g in grp_list:
                    gid = str(g.get('group_id', ''))
                    gname = g.get('group_name', f'Group {gid}')
                    if gid:
                        self.groups[gname] = gid
                page += 1
                time.sleep(0.5)

            self.root.after(0, lambda: self._log(
                f'Loaded {len(self.groups)} folder(s)'))
            self.root.after(0, self._update_group_menu)

        threading.Thread(target=do_load, daemon=True).start()

    def _update_group_menu(self):
        menu = self.group_menu['menu']
        menu.delete(0, 'end')

        menu.add_command(label='--- ALL PROFILES ---',
                         command=lambda: self.group_var.set('--- ALL PROFILES ---'))

        for name in sorted(self.groups.keys()):
            menu.add_command(label=name,
                             command=lambda n=name: self.group_var.set(n))

        if self.groups:
            self.group_var.set(sorted(self.groups.keys())[0])
        else:
            self.group_var.set('--- ALL PROFILES ---')

    def _start_bulk(self):
        if self.running:
            return

        target = self.bulk_var.get()
        selected = self.group_var.get()
        group_id = self.groups.get(selected)
        scope = selected if group_id else 'ALL PROFILES'

        if not messagebox.askyesno('Confirm',
                f'Change WebRTC to "{target}"\n'
                f'for: {scope}?\n\n'
                f'Open profiles need to be closed & reopened.'):
            return

        self.running = True
        self.start_btn.configure(state='disabled', text='Working...')

        def do_change():
            time.sleep(2)
            page = 1
            success = 0
            failed = 0
            total = 0

            while True:
                url = f'/api/v1/user/list?page={page}&page_size=100'
                if group_id:
                    url += f'&group_id={group_id}'

                resp = None
                for attempt in range(5):
                    resp = api_get(url)
                    if resp.get('code') == 0:
                        break
                    if 'Too many request' in resp.get('msg', ''):
                        self.root.after(0, lambda a=attempt: self._log(
                            f'Rate limited, waiting... (retry {a+1}/5)'))
                        time.sleep(3)
                    else:
                        break

                if resp.get('code') != 0:
                    self.root.after(0, lambda: self._log(
                        f'API error on page {page}: {resp.get("msg", "")}'))
                    break

                profiles = resp.get('data', {}).get('list', [])
                if not profiles:
                    break

                for p in profiles:
                    uid = p.get('user_id', '')
                    sn = p.get('serial_number', '')
                    total += 1

                    update_resp = None
                    for attempt in range(3):
                        update_resp = api_post('/api/v1/user/update', {
                            'user_id': uid,
                            'fingerprint_config': {'webrtc': target}
                        })
                        if update_resp.get('code') == 0:
                            break
                        if 'Too many request' in update_resp.get('msg', ''):
                            time.sleep(1.5)
                        else:
                            break

                    if update_resp.get('code') == 0:
                        success += 1
                    else:
                        failed += 1
                        msg = update_resp.get('msg', '')
                        self.root.after(0, lambda s=sn, m=msg:
                            self._log(f'#{s}: FAILED - {m}'))

                    if total % 10 == 0:
                        self.root.after(0, lambda t=total, s=success, f=failed:
                            self.progress_label.configure(
                                text=f'Progress: {t} done, {s} ok, {f} failed'))

                    time.sleep(0.5)

                page += 1

            self.root.after(0, lambda: self._log(
                f'DONE! {scope}: {success} changed. '
                f'Failed: {failed}. Total: {total}.'))
            self.root.after(0, lambda: self.progress_label.configure(
                text=f'DONE: {success}/{total} changed'))
            self.root.after(0, lambda: self.start_btn.configure(
                state='normal', text='CHANGE ALL'))
            self.running = False

        threading.Thread(target=do_change, daemon=True).start()

    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    app = WebRTCChangerApp()
    app.run()
