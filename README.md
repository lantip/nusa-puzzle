# NUSAPUZZLE

An open-source **crossword puzzle platform** designed to support **teachers**, **students**, and **community activists** in learning and preserving **Aksara Nusantara** — the traditional scripts of the Indonesian archipelago, including **Jawa**, **Sunda**, **Bali**, **Pegon**, **Kawi**, **Rejang**, **Lontara**, **Batak**, and others.

Built with ❤️ using **Flask**, **SQLite**, and **Tabler CSS**, this project aims to provide a simple and elegant web platform for educational games, cultural preservation, and community collaboration.

---

## 🌿 Mission

> This project is open for everyone — educators, students, and developers.
> You are free to use, modify, or even build commercial applications based on it.
> However, if you gain financial benefit from it, please consider sharing some of your revenue with those in need. 🙏

---

## 🚀 Features

* 🧠 **Crossword Generator** – Create educational crosswords using Nusantara scripts.
* 🕋️ **Custom Fonts Support** – Choose from local font files (e.g., Aksara Jawa, Sunda, Bali, etc.).
* 🧩 **Interactive Play Mode** – Users can play directly in the browser.
* 🧾 **Scoreboard & Leaderboard** – Tracks performance and ranks users.
* 🖼️ **Automatic Crossword Preview** – Generates visual previews on the fly.
* 🌍 **Public Gallery** – Browse published crosswords from all users.
* 🎓 **Open-Source and Educational Focus** – Perfect for classrooms, workshops, and cultural communities.

---

## 🛠️ Tech Stack

| Component          | Description                                            |
| ------------------ | ------------------------------------------------------ |
| **Backend**        | [Flask](https://flask.palletsprojects.com/) (Python 3) |
| **Database**       | SQLite (default) — easy to migrate to PostgreSQL/MySQL |
| **Frontend**       | [Tabler CSS](https://tabler.io/), Bootstrap utilities  |
| **Templating**     | Jinja2                                                 |
| **ORM**            | SQLAlchemy                                             |
| **Icons**          | Tabler Icons                                           |
| **Font Rendering** | Web fonts + Local `/static/font/` directory            |

---

## 📦 Requirements

Make sure you have **Python 3.9+** installed.

### Dependencies

All dependencies are managed via **Pipenv**:

```bash
pip install pipenv
pipenv install
```

If you’re not using Pipenv, you can install manually:

```bash
pip install flask sqlalchemy flask-login flask-migrate flask-bcrypt
```

Optional but recommended:

```bash
pip install pillow
```

---

## ⚙️ Configuration

1. Clone the repository:

   ```bash
   git clone https://github.com/lantip/nusa-puzzle.git
   cd nusa-puzzle
   ```

2. Initialize the environment:

   ```bash
   pipenv shell
   ```

3. Set up the database:

   ```bash
   flask db upgrade
   ```

4. Run the app:

   ```bash
   flask run
   ```

5. Visit:

   ```
   http://127.0.0.1:5000
   ```

---

## 🧰 Project Structure

```
.
├── app.py
├── crossword/
│   ├── __init__.py
│   └── generator.py
├── models.py
├── utils.py
├── static/
│   ├── css/
│   ├── font/
│   ├── img/
│   ├── js/
│   └── logo.svg
├── templates/
│   ├── admin/
│   ├── auth/
│   ├── landing/
│   ├── play/
│   └── base.html
└── README.md
```

---

## 🐇️ Core Features

### Crossword Creation

* Users can create new crosswords with clues and answers.
* Option to upload or select a custom font from `/static/font/`.
* Supports Aksara Nusantara fonts.

### Game Play

* Interactive crossword UI.
* Auto-check answers and calculate score.
* Animated result summary after submission.

### Leaderboard

* Per-crossword leaderboard.
* Global leaderboard across all crosswords.
* Guest and registered users are both supported.

### Game List

* `/list-games` displays all published crosswords.
* Includes random game button (“Mainkan Random”).
* Each game card shows author, play count, and preview image.

---

## 🖼️ Crossword Preview

When the preview image (`crossword-preview.png`) does not exist, the system can **generate one automatically** from the crossword grid.
You can modify the preview generator in `utils.py` to use Pillow, Selenium, or any HTML-to-image library.

---

## 📊 Leaderboards

The system keeps track of:

* **Per-crossword scores**
* **Global leaderboard** that aggregates top scores across all games.

Duplicate scores per user are automatically filtered to show only their **highest score**.

---

## 🔐 Terms and Privacy

You can view the built-in policy pages:

* `/terms` → **Syarat dan Ketentuan**
* `/privacy` → **Kebijakan Privasi**

These pages reflect the community and educational values of this project.

---

## 🤝 Contributing

1. Fork the repository
2. Create a new branch (`feature/my-feature`)
3. Commit your changes
4. Push to your fork
5. Submit a Pull Request

We welcome improvements — whether UI enhancements, bug fixes, or new features like multiplayer mode, teacher dashboards, or more script support.

---

## 📜 License & Ethics

This project is released under the **MIT License**, meaning:

* You can freely use, modify, distribute, and even sell derivative works.
* **No warranty** is provided.
* However, we encourage every user who gains financially from this project to **donate a portion of their revenue to the poor or to educational causes.**

> “Ilmu yang bermanfaat adalah ilmu yang dibagikan.”
> — Semangat Gotong Royong Nusantara 🇮🇩

---

## 🌐 Acknowledgements

* [Tabler.io](https://tabler.io) for the beautiful UI components
* [Flask](https://flask.palletsprojects.com/) for simplicity and flexibility
* Educators and cultural activists who preserve Aksara Nusantara
* Open-source community contributors everywhere 🌏

---

### 🧑‍🛏️ Contact

For suggestions or collaboration, please visit:
👉 [GitHub Repository](https://github.com/lantip/nusa-puzzle)

---

### ❤️ Support the Mission

If this project helps your teaching, community, or organization —
please share it, contribute back, or help those in need.
That’s how we keep the spirit of **Nusantara** alive.
