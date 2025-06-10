import tkinter as tk
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText
from PIL import Image, ImageTk
from chatbot import message_queue
import threading
import asyncio
import chatbot
import os
import json
from screenshot import screenshot

class PTZApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PTZ Preset Loader")

        self.main_frame = tk.Frame(root)
        self.main_frame.pack(fill='both', expand=True)

        cam_frame = tk.Frame(self.main_frame)
        cam_frame.grid(row=0, column=0, padx=5, pady=5, sticky='n')

        # Camera list label
        self.cam_label = tk.Label(cam_frame, text="Cams:")
        self.cam_label.pack()

        # Camera list
        self.cam_listbox = tk.Listbox(cam_frame, name="cam_listbox", height=10, exportselection=False)
        self.cam_listbox.pack()
        self.cam_listbox.bind("<<ListboxSelect>>", self.on_cam_select)

        cam_btn_frame = tk.Frame(cam_frame)
        cam_btn_frame.pack(pady=5)

        self.add_cam_btn = tk.Button(cam_btn_frame, text="Add Camera", command=self.open_add_camera_popup)
        self.add_cam_btn.pack(side=tk.LEFT, padx=(0,5))

        self.del_cam_btn = tk.Button(cam_btn_frame, text='Delete Camera', command=self.delete_camera)
        self.del_cam_btn.pack(side=tk.LEFT)
        
        # Multicam list label
        self.multicam_label = tk.Label(cam_frame, text="Multicams:")
        self.multicam_label.pack()

        # Multicam list
        self.multicam_listbox = tk.Listbox(cam_frame, height=10)
        self.multicam_listbox.pack()
        self.multicam_listbox.bind("<<ListboxSelect>>", self.on_multicam_select)

        multicam_btn_frame = tk.Frame(cam_frame)
        multicam_btn_frame.pack(pady=5)

        self.add_multicam_btn = tk.Button(multicam_btn_frame, text="Add Multicam", command=self.open_add_multicam_popup)
        self.add_multicam_btn.pack(side=tk.LEFT, padx=(0,5))

        self.del_multicam_btn = tk.Button(multicam_btn_frame, text="Delete Multicam", command=self.delete_multicam)
        self.del_multicam_btn.pack(side=tk.LEFT)

        self.load_camera_data()

        # Preset frame
        preset_frame = tk.Frame(self.main_frame)
        preset_frame.grid(row=0, column=1, padx=5, pady=5, sticky='n')

        # Button to update preset list
        self.button = tk.Button(preset_frame, text="Sync PTZ Presets", command=self.send_ptzlist)
        self.button.pack()

        # Preset list
        self.preset_list = tk.Listbox(preset_frame, selectmode='multiple', height=20)
        self.preset_list.pack()
        self.preset_list.bind("<<ListboxSelect>>", self.on_preset_select)

        # Frame to make the select buttons show on the same row
        preset_btn_frame = tk.Frame(preset_frame)
        preset_btn_frame.pack(pady=5)

        self.select_all_btn = tk.Button(preset_btn_frame, text="Select All", command=self.select_all_presets)
        self.select_all_btn.pack(side=tk.LEFT, padx=(0,5))

        self.deselect_all_btn = tk.Button(preset_btn_frame, text="Deselect All", command=self.deselect_all_presets)
        self.deselect_all_btn.pack(side=tk.LEFT)

        # Image update button
        image_update_btn = tk.Button(self.main_frame, text='Update Selected Image(s)', command=self.update_images)
        image_update_btn.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky='n')

        # Scrollable preset image display area
        self.image_frame = tk.Frame(self.main_frame)
        self.image_frame.grid(row=0, column=2, padx=5, pady=5, sticky='n')

        self.canvas = tk.Canvas(self.image_frame, width=540, height=410)
        self.scrollbar = tk.Scrollbar(self.image_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Twitch chat
        self.chat_box = ScrolledText(self.main_frame, state='disabled', wrap='word', height=25, width=40)
        self.chat_box.grid(row=0, column=3, padx=5, pady=5, sticky='n')
        self.poll_queue()

        # Register callback
        chatbot.set_presets_callback(self.on_presets_received)

    def poll_queue(self):
        while not message_queue.empty():
            message = message_queue.get()
            self.display_message(message)
        self.root.after(100, self.poll_queue)

    def display_message(self, msg):
        self.chat_box.config(state='normal')
        self.chat_box.insert(tk.END, msg + '\n')
        self.chat_box.yview(tk.END)
        self.chat_box.config(state='disabled')

    def get_current_image(self, item_name, update_type, camname):
        if update_type == 'preset':
            image_path = os.path.join(f'images/{camname}', f'{item_name}.png')
        elif update_type == 'multicam':
            image_path = os.path.join('images', f'{item_name}.png')
        
        try:
            image = Image.open(image_path)
            image = image.resize((320, 180))
            return image
        except Exception as e:
            return Image.new("RGB", (320, 180), "gray")

    def get_new_image(self, item_name, update_type, camname):
        new_image = screenshot(item_name, update_type, camname)
        try:
            image = Image.open(new_image)
            image = image.resize((320, 180))
            return image
        except Exception as e:
            return Image.new("RGB", (320, 180), "gray")

    def save_new_image(self, item_name, update_type, camname, image):
        if update_type == 'preset':
            src_path = f'images/tmp/{camname}/{item_name}.png'
            dst_dir = f'images/{camname}'
        elif update_type == 'multicam':
            src_path = f'images/tmp/{item_name}.png'
            dst_dir = 'images'
        
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)
        dst_path = os.path.join(dst_dir, f'{item_name}.png')

        os.replace(src_path, dst_path)

    def update_images(self):
        selected_cam_index = self.cam_listbox.curselection()
        selected_multicam_index = self.multicam_listbox.curselection()
        selected_presets_index = self.preset_list.curselection()

        if hasattr(self, 'image_update_frame'):
            self.image_update_frame.destroy()

        # Area for existing vs new image display
        self.image_update_frame = tk.Frame(self.main_frame)
        self.image_update_frame.grid(row=1, column=2, padx=5, pady=5, sticky='n')
        camname = None
        if selected_cam_index:
            camname = self.cam_listbox.get(selected_cam_index[0])
            if not selected_presets_index:
                messagebox.showerror('Error', 'Please select at least one preset from the list.')
                return
            select_type = 'preset'
            preset_items = [self.preset_list.get(i) for i in selected_presets_index]
        elif selected_multicam_index:
            multicamname = self.multicam_listbox.get(selected_multicam_index[0])
            select_type = 'multicam'
            preset_items = [multicamname]
        else:
            messagebox.showerror('Error', 'Please select a camera and preset(s) or multicam from the list.')
            return
        
        self.update_index = 0
        self.update_cam_name = camname
        self.update_type = select_type
        self.update_items = preset_items
        self.update_new_images = {}

        self.update_title = tk.Label(self.image_update_frame, text='')
        self.update_title.grid(row=0, column=0, columnspan=2, pady=(0, 10))

        self.curr_title = tk.Label(self.image_update_frame, text='Current Image')
        self.curr_title.grid(row=1, column=0)

        self.new_title = tk.Label(self.image_update_frame, text='New Image')
        self.new_title.grid(row=1, column=1)

        self.current_img_label = tk.Label(self.image_update_frame)
        self.current_img_label.grid(row=2, column=0)

        self.new_img_label = tk.Label(self.image_update_frame)
        self.new_img_label.grid(row=2, column=1)

        self.prev_btn = tk.Button(self.image_update_frame, text='<< Previous', command=self.go_prev)
        self.prev_btn.grid(row=3, column=0, padx=5, pady=5)

        self.next_btn = tk.Button(self.image_update_frame, text='Next >>', command=self.go_next)
        self.next_btn.grid(row=3, column=1, padx=5, pady=5)

        self.image_update_btn_frame = tk.Frame(self.main_frame)
        self.image_update_btn_frame.grid(row=1, column=3, padx=5, pady=5, sticky='n')

        self.retake_btn = tk.Button(self.image_update_btn_frame, text='Retake', font=("Arial", 24, "bold"), command=self.retake_image)
        self.retake_btn.pack(padx=5, pady=5)

        self.accept_btn = tk.Button(self.image_update_btn_frame, text='Accept', font=("Arial", 24, "bold"), command=self.accept_image)
        self.accept_btn.pack(padx=5, pady=5)

        self.run_preset_btn = tk.Button(self.image_update_btn_frame, text='Run Preset', font=("Arial", 24, "bold"), command=self.run_preset)
        self.run_preset_btn.pack(padx=5, pady=5)

        self.refresh_image_update_ui()

    def refresh_image_update_ui(self):
        item = self.update_items[self.update_index]
        camname = self.update_cam_name
        update_type = self.update_type

        self.update_title.config(text=f'Updating: {item}')

        current_img = self.get_current_image(item, update_type, camname)
        new_img = self.update_new_images.get(item) or Image.new("RGB", (320, 180), "gray")
        self.update_new_images[item] = new_img

        self.curr_photo = ImageTk.PhotoImage(current_img)
        self.new_photo = ImageTk.PhotoImage(new_img)

        self.current_img_label.config(image=self.curr_photo)
        self.new_img_label.config(image=self.new_photo)

        self.prev_btn.config(state=tk.NORMAL if self.update_index > 0 else tk.DISABLED)
        self.next_btn.config(state=tk.NORMAL if self.update_index < len(self.update_items) - 1 else tk.DISABLED)

    def retake_image(self):
        item = self.update_items[self.update_index]
        camname = self.update_cam_name
        update_type = self.update_type
        self.update_new_images[item] = self.get_new_image(item, update_type, camname)
        self.refresh_image_update_ui()

    def accept_image(self):
        item = self.update_items[self.update_index]
        camname = self.update_cam_name
        update_type = self.update_type
        self.save_new_image(item, update_type, camname, self.update_new_images[item])

    def go_next(self):
        if self.update_index < len(self.update_items) - 1:
            self.update_index += 1
            self.refresh_image_update_ui()

    def go_prev(self):
        if self.update_index > 0:
            self.update_index -= 1
            self.refresh_image_update_ui()

    def run_preset(self):
        item = self.update_items[self.update_index]
        camname = self.update_cam_name
        update_type = self.update_type

        # multicams don't have presets
        if update_type == 'multicam':
            return

        if chatbot.chat_instance is None:
            messagebox.showerror("Error", "Bot is not ready yet. Please wait.")
            return
        # Send the !ptzload command to chat
        asyncio.run_coroutine_threadsafe(
            chatbot.send_message(f"!ptzload {camname} {item}"), chatbot.loop
        )

    def load_preset_list(self, cam_index=None):
        if cam_index:
            self.cam_listbox.selection_set(cam_index[0])
        else:
            cam_index = self.cam_listbox.curselection()
        presets = self.camera_data['cameras'][cam_index[0]]['presets']
        self.preset_list.delete(0, tk.END)
        for preset in presets:
            self.preset_list.insert(tk.END, preset)

    def load_camera_data(self):
        try:
            with open('cameras.json', 'r') as f:
                self.camera_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.camera_data = {'cameras': [], 'multicams': []}

        # Clear and fill cam_listbox
        self.cam_listbox.delete(0, tk.END)
        for cam in self.camera_data['cameras']:
            self.cam_listbox.insert(tk.END, cam['name'])

        # Clear and fill multicam_listbox
        self.multicam_listbox.delete(0, tk.END)
        for multicam in self.camera_data['multicams']:
            self.multicam_listbox.insert(tk.END, multicam['name'])
    
    def save_camera_data(self):
        with open('cameras.json', 'w') as f:
            json.dump(self.camera_data, f, indent=2)

    def delete_camera(self):
        try:
            selected_index = self.cam_listbox.curselection()[0]
            selected_name = self.cam_listbox.get(selected_index)
        except IndexError:
            messagebox.showwarning('No Selection', 'Please select a camera to delete.')

        confirm = messagebox.askyesno('Confirm Deletion', f'Are you sure you want to delete "{selected_name}"')

        if not confirm:
            return
        
        before_count = len(self.camera_data['cameras'])
        self.camera_data['cameras'] = [
            c for c in self.camera_data['cameras'] if c['name'] != selected_name
        ]
        after_count = len(self.camera_data['cameras'])

        if before_count == after_count:
            messagebox.showerror('Error', 'Camera not found or could not be deleted.')
            return
        
        self.save_camera_data()
        self.load_camera_data()

    def delete_multicam(self):
        try:
            selected_index = self.multicam_listbox.curselection()[0]
            selected_name = self.multicam_listbox.get(selected_index)
        except IndexError:
            messagebox.showwarning('No Selection', 'Please select a Multicam to delete.')

        confirm = messagebox.askyesno('Confirm Deletion', f'Are you sure you want to delete "{selected_name}"')

        if not confirm:
            return
        
        before_count = len(self.camera_data['multicams'])
        self.camera_data['multicams'] = [
            m for m in self.camera_data['multicams'] if m['name'] != selected_name
        ]
        after_count = len(self.camera_data['multicams'])

        if before_count == after_count:
            messagebox.showerror('Error', 'Multicam not found or could not be deleted.')
            return
        
        self.save_camera_data()
        self.load_camera_data()

    def on_cam_select(self, event=None):
        selection = self.cam_listbox.curselection()
        if not selection:
            return
        self.multicam_listbox.selection_clear(0, tk.END)

        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.load_preset_list()

        camname = self.cam_listbox.get(selection)

        self.loaded_images = []

        col_count = 3

        presets = self.camera_data['cameras'][selection[0]]['presets']
        for i, preset in enumerate(presets):
            image_path = os.path.join(f'images/{camname}', f'{preset}.png')

            row = i // col_count
            col = i % col_count

            try:
                image = Image.open(image_path)
                image = image.resize((160, 90))
                photo = ImageTk.PhotoImage(image)
                self.loaded_images.append(photo)

                # Image label
                img_label = tk.Label(self.scrollable_frame, image=photo)
                img_label.grid(row=row*2, column=col, padx=10, pady=(10, 0))

                # Title label
                title_label = tk.Label(self.scrollable_frame, text=preset)
                title_label.grid(row=row*2+1, column=col, padx=10, pady=(0, 10))
            except Exception as e:
                error_label = tk.Label(self.scrollable_frame, text=f"{preset} - Not found", bg="gray", width=20, height=5)
                error_label.grid(row=row*2, column=col, padx=10, pady=10)

    def on_multicam_select(self, event=None):
        selection = self.multicam_listbox.curselection()
        if not selection:
            return
        self.cam_listbox.selection_clear(0, tk.END)

        self.preset_list.delete(0, tk.END)

        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

    def on_preset_select(self, event=None):
        pass

    def open_add_camera_popup(self):
        popup = tk.Toplevel(self.root)
        popup.title("Add Camera")
        popup.geometry("300x200")
        popup.transient(self.root)
        popup.grab_set()

        tk.Label(popup, text="Camera Name:").pack(pady=(10, 0))
        name_entry = tk.Entry(popup)
        name_entry.pack(pady=5)

        def submit():
            name = name_entry.get().strip()
            if name:
                if name in self.camera_data['cameras']:
                    messagebox.showwarning('Duplicate', 'Camera already exists.')
                    return
                self.camera_data['cameras'].append({
                    "name": name,
                    "presets": []
                })
                self.save_camera_data()
                self.load_camera_data()
                popup.destroy()
            else:
                messagebox.showwarning("Input Error", "Camera name cannot be empty.")

        btn_frame = tk.Frame(popup)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Add", command=submit).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", command=popup.destroy).pack(side=tk.LEFT, padx=5)

    def open_add_multicam_popup(self):
        popup = tk.Toplevel(self.root)
        popup.title("Add MultiCam")
        popup.geometry("350x400")
        popup.transient(self.root)
        popup.grab_set()

        # 1. MultiCam Name
        tk.Label(popup, text="MultiCam Name:").pack(pady=(10, 0))
        name_entry = tk.Entry(popup)
        name_entry.pack(pady=5)

        # Get all existing camera names
        all_cams = self.cam_listbox.get(0, tk.END)

        # 2. Primary Camera Dropdown
        tk.Label(popup, text="Primary Camera:").pack(pady=(10, 0))
        primary_var = tk.StringVar()
        primary_var.set(all_cams[0] if all_cams else "")  # Default selection
        primary_dropdown = tk.OptionMenu(popup, primary_var, *all_cams)
        primary_dropdown.pack(pady=5)

        # 3. PiP Camera Multi-Select Listbox
        tk.Label(popup, text="PiP Cameras:").pack(pady=(10, 0))
        pip_listbox = tk.Listbox(popup, selectmode='multiple', exportselection=False, height=8)
        pip_listbox.pack(pady=5, fill="both", expand=True)

        def update_pip_listbox(*args):
            # Refresh PiP options excluding the selected primary cam
            pip_listbox.delete(0, tk.END)
            selected_primary = primary_var.get()
            for cam in all_cams:
                if cam != selected_primary:
                    pip_listbox.insert(tk.END, cam)

        # Bind primary cam selection change to update pip list
        primary_var.trace_add("write", update_pip_listbox)
        update_pip_listbox()

        # 4. Submit and Cancel Buttons
        def submit():
            name = name_entry.get().strip()
            primary = primary_var.get()
            pip_cams = [pip_listbox.get(i) for i in pip_listbox.curselection()]

            if not name:
                messagebox.showwarning("Input Error", "MultiCam name is required.")
            elif not primary:
                messagebox.showwarning("Input Error", "Primary camera must be selected.")
            elif not pip_cams:
                messagebox.showwarning("Input Error", "At least one PiP camera is required.")
            elif name in [m['name'] for m in self.camera_data['multicams']]:
                messagebox.showwarning('Duplicate', 'Multicam with this name already exists.')
            else:
                self.camera_data['multicams'].append({
                    'name': name,
                    'primary': primary,
                    'pips': pip_cams
                })
                self.save_camera_data()
                self.load_camera_data()
                popup.destroy()

        btn_frame = tk.Frame(popup)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Add", command=submit).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", command=popup.destroy).pack(side=tk.LEFT, padx=5)

    def select_all_presets(self):
        self.preset_list.select_set(0, tk.END)
        self.on_preset_select()

    def deselect_all_presets(self):
        self.preset_list.select_clear(0, tk.END)
        self.on_preset_select()

    def send_ptzlist(self):
        cam_index = self.cam_listbox.curselection()
        if cam_index:
            camname = self.cam_listbox.get(cam_index[0])
        else:
            messagebox.showerror("Error", "Please select a camera from the list.")
            return
        if chatbot.chat_instance is None:
            messagebox.showerror("Error", "Bot is not ready yet. Please wait.")
            return
        chatbot.waiting_for_ptz_presets = True
        # Send the !ptzlist <camname> command to chat
        asyncio.run_coroutine_threadsafe(
            chatbot.send_message(f"!ptzlist {camname}"), chatbot.loop
        )

    def on_presets_received(self, presets):
        # print("Callback received presets:", presets)
        # This is called from the bot thread, so use `after` to update GUI safely
        self.root.after(0, self.update_presets, presets)

    def update_presets(self, presets):
        cam_index = self.cam_listbox.curselection()

        self.camera_data['cameras'][cam_index[0]]['presets'] = presets
        self.save_camera_data()
        self.load_camera_data()
        self.load_preset_list(cam_index)

def start_bot():
    chatbot.loop = asyncio.new_event_loop()
    asyncio.set_event_loop(chatbot.loop)
    chatbot.loop.run_until_complete(chatbot.run())

if __name__ == "__main__":
    # Start the bot in a separate thread
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()

    # Start the GUI
    root = tk.Tk()
    root.geometry("1400x800")
    app = PTZApp(root)
    root.mainloop()