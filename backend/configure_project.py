"""Local desktop settings editor. Credentials are never sent to the frontend."""
import json
import os
import secrets
import tempfile
from pathlib import Path
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent


def save_settings(path, updates):
    values = dict(dotenv_values(path)) if path.exists() else {}
    values.update(updates)
    if not values.get('JWT_SECRET') or values['JWT_SECRET'].startswith('REPLACE_'):
        values['JWT_SECRET'] = secrets.token_urlsafe(48)
    text = '\n'.join(f'{key}={json.dumps(value, ensure_ascii=False)}'
                     for key, value in values.items() if value is not None) + '\n'
    descriptor, temporary = tempfile.mkstemp(prefix='.env-write-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as output:
            output.write(text)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    import tkinter as tk
    from tkinter import ttk, messagebox
    path = ROOT / '.env'
    values = dotenv_values(path if path.exists() else ROOT / '.env.example')
    window = tk.Tk()
    window.title('Folio — Project setup')
    window.geometry('760x560')
    frame = ttk.Frame(window, padding=24)
    frame.pack(fill='both', expand=True)
    ttk.Label(frame, text='Folio project settings', font=('Segoe UI', 20, 'bold')).pack(anchor='w')
    ttk.Label(frame, text='Saved locally in backend/.env. Restart the API and worker after saving.').pack(anchor='w', pady=(8, 16))
    fields = {}
    definitions = [
        ('DATABASE_URL', 'MySQL database URL', 'mysql+pymysql://docqa:YOUR_PASSWORD@127.0.0.1:3306/document_qa'),
        ('CHAT_PROVIDER', 'Chat provider (blank = same as embeddings)', 'openai-compatible'),
        ('CHAT_BASE_URL', 'Chat API base URL', 'https://api.groq.com/openai/v1'),
        ('CHAT_API_KEY', 'Chat API key', ''),
        ('LLM_MODEL', 'Chat model', 'qwen/qwen3.8-27b'),
        ('AI_BASE_URL', 'Local embedding server', 'http://127.0.0.1:11434'),
        ('EMBEDDING_MODEL', 'Embedding model', 'nomic-embed-text'),
    ]
    for key, label, default in definitions:
        row = ttk.Frame(frame)
        row.pack(fill='x', pady=5)
        ttk.Label(row, text=label, width=37).pack(side='left')
        field = ttk.Entry(row, show='*' if key in {'CHAT_API_KEY', 'DATABASE_URL'} else '')
        field.insert(0, values.get(key) if values.get(key) is not None else default)
        field.pack(side='left', fill='x', expand=True)
        fields[key] = field
    def save():
        updates = {key: field.get().strip() for key, field in fields.items()}
        if updates['CHAT_PROVIDER'] not in {'', 'ollama', 'openai-compatible'}:
            messagebox.showerror('Invalid settings', 'Choose ollama or openai-compatible for chat.')
            return
        if updates['CHAT_PROVIDER'] and not updates['CHAT_BASE_URL'].startswith(('http://', 'https://')):
            messagebox.showerror('Invalid settings', 'Enter an HTTP or HTTPS chat API base URL.')
            return
        if not updates['DATABASE_URL'].startswith('mysql+pymysql://'):
            messagebox.showerror('Invalid settings', 'Enter a MySQL URL beginning with mysql+pymysql://.')
            return
        try:
            if not path.exists():
                # Initialize all example settings, while preserving a generated secret.
                save_settings(path, dict(values))
            save_settings(path, updates)
        except OSError:
            messagebox.showerror('Save failed', 'Cannot write backend/.env. Check folder permissions.')
            return
        messagebox.showinfo('Settings saved', 'Saved to backend/.env. Restart API and worker. No database migrations were run.')
    ttk.Button(frame, text='Save settings', command=save).pack(anchor='e', pady=18)
    ttk.Label(frame, text='Groq receives questions and retrieved excerpts when hosted chat is enabled.\nKeep keys private. Changing embedding models requires document reindexing.', wraplength=690).pack(anchor='w')
    window.mainloop()


if __name__ == '__main__':
    main()
