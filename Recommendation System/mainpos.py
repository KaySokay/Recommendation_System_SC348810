import tkinter as tk
from src.pos_ui import POSUI
import os

if __name__ == "__main__":
    data_folder = './data'
    if not os.path.exists(data_folder):
        os.makedirs(data_folder)
        print(f"Created data folder: {data_folder}")
    root = tk.Tk()
    app = POSUI(root)
    root.mainloop()
