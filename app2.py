import sys
import json
import sqlite3
import argparse
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import List, Optional
from PyQt5 import QtWidgets, QtCore, QtGui, QtNetwork
import yt_dlp
import re
import requests
from bs4 import BeautifulSoup
import threading
import time

@dataclass
class PostData:
    url: str
    title: str
    platform: str
    description: str
    tags: List[str]
    images: List[str]
    group: str = ""  # New field for grouping

class StorageInterface(ABC):
    @abstractmethod
    def save_post(self, post: PostData): pass

    @abstractmethod
    def get_all_posts(self) -> List[PostData]: pass

class JSONStorage:
    def __init__(self, filename='posts.json'):
        self.filename = filename
        self.load()

    def load(self):
        try:
            with open(self.filename, 'r') as f:
                data = json.load(f)
            self.posts = [PostData(**p) for p in data.get("posts", [])]
            self.groups = data.get("groups", [])
        except Exception:
            self.posts = []
            self.groups = []

    def save(self):
        with open(self.filename, 'w') as f:
            json.dump({
                "posts": [asdict(p) for p in self.posts],
                "groups": self.groups,
            }, f, indent=2)

    def all_posts(self):
        return self.posts

    def all_groups(self):
        return self.groups

class SQLiteStorage(StorageInterface):
    def __init__(self, db_path='data.db'):
        self.conn = sqlite3.connect(db_path)
        self._init_db()

    def _init_db(self):
        self.conn.execute('''CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY,
            title TEXT,
            description TEXT,
            tags TEXT,
            images TEXT,
            platform TEXT,
            url TEXT
        )''')

    def save_post(self, post: PostData):
        self.conn.execute('INSERT INTO posts (title, description, tags, images, platform, url) VALUES (?, ?, ?, ?, ?, ?)',
                          (post.title, post.description, json.dumps(post.tags), json.dumps(post.images), post.platform, post.url))
        self.conn.commit()

    def get_all_posts(self) -> List[PostData]:
        cursor = self.conn.execute('SELECT title, description, tags, images, platform, url FROM posts')
        return [PostData(title, desc, json.loads(tags), json.loads(images), platform, url) for title, desc, tags, images, platform, url in cursor]


class BaseFetcher:
    def fetch(self, url):
        return PostData(
            url=url,
            title="Sample Title",
            platform=self.__class__.__name__,
            description="Some description about the post.",
            tags=["tag1", "tag2"],
            images=["https://via.placeholder.com/160x90"],
        )

class YouTubeFetcher:
    def fetch(self, url: str) -> Optional[PostData]:
        ydl_opts = {'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return PostData(
                title=info.get('title', ''),
                description=info.get('description', ''),
                tags=info.get('tags', []),
                images=[info.get('thumbnail')] if info.get('thumbnail') else [],
                platform='YouTube',
                url=url
            )

class InstagramFetcher:
    def fetch(self, url: str) -> Optional[PostData]:
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            scripts = soup.find_all('script', type="application/ld+json")
            for script in scripts:
                data = json.loads(script.string)
                if isinstance(data, dict) and 'caption' in data:
                    description = data.get('caption', '')
                    image = data.get('image', '')
                    return PostData(
                        title="Instagram Post",
                        description=description,
                        tags=re.findall(r"#(\w+)", description),
                        images=[image] if image else [],
                        platform="Instagram",
                        url=url
                    )
        except Exception as e:
            print(f"Instagram fetch error: {e}")
        return None

class FacebookFetcher:
    def fetch(self, url: str) -> Optional[PostData]:
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            desc = soup.find('meta', property='og:description')
            image = soup.find('meta', property='og:image')
            description = desc['content'] if desc else ""
            image_url = image['content'] if image else ""
            return PostData(
                title="Facebook Post",
                description=description,
                tags=re.findall(r"#(\w+)", description),
                images=[image_url] if image_url else [],
                platform="Facebook",
                url=url
            )
        except Exception as e:
            print(f"Facebook fetch error: {e}")
        return None

class LinkedInFetcher:
    def fetch(self, url: str) -> Optional[PostData]:
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            desc = soup.find('meta', property='og:description')
            image = soup.find('meta', property='og:image')
            description = desc['content'] if desc else ""
            image_url = image['content'] if image else ""
            return PostData(
                title="LinkedIn Post",
                description=description,
                tags=re.findall(r"#(\w+)", description),
                images=[image_url] if image_url else [],
                platform="LinkedIn",
                url=url
            )
        except Exception as e:
            print(f"LinkedIn fetch error: {e}")
        return None

class PinterestFetcher:
    def fetch(self, url: str) -> Optional[PostData]:
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            desc = soup.find('meta', property='og:description')
            image = soup.find('meta', property='og:image')
            title = soup.find('meta', property='og:title')
            description = desc['content'] if desc else ""
            image_url = image['content'] if image else ""
            title_text = title['content'] if title else "Pinterest Post"
            return PostData(
                title=title_text,
                description=description,
                tags=re.findall(r"#(\w+)", description),
                images=[image_url] if image_url else [],
                platform="Pinterest",
                url=url
            )
        except Exception as e:
            print(f"Pinterest fetch error: {e}")
        return None

class GenericFetcher:
    def fetch(self, url: str) -> Optional[PostData]:
        return PostData(
            title="Generic Title",
            description="Example project description from unknown source",
            tags=["example", "demo"],
            images=["https://via.placeholder.com/150"],
            platform="Unknown",
            url=url
        )

class BaseFetcher:
    def fetch(self, url):
        return PostData(url=url, title="Sample Title", platform=self.__class__.__name__,
                    description="Some description about the post.",
                    tags=["tag1", "tag2"],
                    images=["https://via.placeholder.com/160x90"])

class ImageLoader(QtCore.QObject):
    finished = QtCore.pyqtSignal(int, QtGui.QPixmap)
    error = QtCore.pyqtSignal(int)

    def __init__(self, row, url):
        super().__init__()
        self.row = row
        self.url = url

    @QtCore.pyqtSlot()
    def load(self):
        try:
            resp = requests.get(self.url, stream=True, timeout=10)
            resp.raise_for_status()
            img_data = resp.content
            pixmap = QtGui.QPixmap()
            if not pixmap.loadFromData(img_data):
                raise Exception("Failed to load pixmap")
            self.finished.emit(self.row, pixmap)
        except Exception as e:
            print(f"Image load error for row {self.row}, url {self.url}: {e}")
            self.error.emit(self.row)
        
        

class PostApp(QtWidgets.QMainWindow):
    def __init__(self, storage: StorageInterface):
        super().__init__()
        
        self.setWindowIcon(QtGui.QIcon('icon.png'))
        
        self.setWindowTitle("Post Viewer with Groups")
        self.resize(1280, 720)



        self.posts: List[PostData] = storage.all_posts()
        self.groups: List[str] = storage.all_groups()

        # Widgets
        self.group_list = QtWidgets.QListWidget()
        self.group_list.setMaximumWidth(150)
        self.group_list.addItem("All")
        for g in self.groups:
            self.group_list.addItem(g)
        self.group_list.currentItemChanged.connect(self.update_display)

        self.url_input = QtWidgets.QLineEdit()
        self.url_input.setPlaceholderText("Enter post URL")
        self.add_btn = QtWidgets.QPushButton("Add Post")
        self.add_btn.clicked.connect(self.add_post)

        self.group_input = QtWidgets.QComboBox()
        self.group_input.setMinimumWidth(100)
        self.group_input.addItem("")  # No group
        self.group_input.addItems(self.groups)

        self.new_group_input = QtWidgets.QLineEdit()
        self.new_group_input.setPlaceholderText("New group name")
        self.new_group_input.setMaximumWidth(100)
        self.new_group_btn = QtWidgets.QPushButton("Add Group")
        self.new_group_btn.setMaximumWidth(75)
        self.new_group_btn.clicked.connect(self.add_group)

        self.filter_input = QtWidgets.QLineEdit()
        self.filter_input.setPlaceholderText("Filter by text or tag")
        self.filter_input.textChanged.connect(self.update_display)

        self.sort_box = QtWidgets.QComboBox()
        self.sort_box.addItems(["Title", "Platform", "Group"])
        self.sort_box.currentIndexChanged.connect(self.update_display)

        self.export_btn = QtWidgets.QPushButton("Export JSON")
        self.export_btn.clicked.connect(self.export_json)
        self.import_btn = QtWidgets.QPushButton("Import JSON")
        self.import_btn.clicked.connect(self.import_json)

        # Table
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["Image", "Title", "Platform", "Tags", "Description", "URL", "Group", "Delete"])
        

        # Layouts
        controls_layout = QtWidgets.QHBoxLayout()
        controls_layout.addWidget(self.url_input)
        controls_layout.addWidget(self.group_input)
        controls_layout.addWidget(self.add_btn)

        group_add_layout = QtWidgets.QHBoxLayout()
        group_add_layout.addWidget(self.new_group_input)
        group_add_layout.addWidget(self.new_group_btn)

        filter_sort_layout = QtWidgets.QHBoxLayout()
        filter_sort_layout.addWidget(self.filter_input)
        filter_sort_layout.addWidget(self.sort_box)
        filter_sort_layout.addWidget(self.export_btn)
        filter_sort_layout.addWidget(self.import_btn)

        left_layout = QtWidgets.QVBoxLayout()
        left_layout.addWidget(QtWidgets.QLabel("Groups"))
        left_layout.addWidget(self.group_list)
        left_layout.addLayout(group_add_layout)

        main_layout = QtWidgets.QHBoxLayout()
        main_layout.addLayout(left_layout)
        right_layout = QtWidgets.QVBoxLayout()
        right_layout.addLayout(controls_layout)
        right_layout.addLayout(filter_sort_layout)
        right_layout.addWidget(self.table)
        main_layout.addLayout(right_layout)

        container = QtWidgets.QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        self.update_display()

    @QtCore.pyqtSlot(int, QtGui.QPixmap)
    def on_image_loaded(self, row, pixmap):
        label = QtWidgets.QLabel()
        max_width = 160
        max_height = 120  # or any other constraint
        
        scaled_pixmap = pixmap.scaled(max_width, max_height, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        label.setPixmap(scaled_pixmap)
        label.setAlignment(QtCore.Qt.AlignCenter)
        
        label.setFixedSize(max_width, max_height)
        label.setScaledContents(False)
        
        self.table.setRowHeight(row, max_height)
        self.table.setCellWidget(row, 0, label)

    @QtCore.pyqtSlot(int)
    def on_image_error(self, row):
        self.table.setItem(row, 0, QtWidgets.QTableWidgetItem("Image Error"))

    def detect_fetcher(self, url: str):
        if "youtube.com" in url or "youtu.be" in url:
            return YouTubeFetcher()
        elif "instagram.com" in url:
            return InstagramFetcher()
        elif "facebook.com" in url:
            return FacebookFetcher()
        elif "linkedin.com" in url:
            return LinkedInFetcher()
        elif "pinterest.com" in url:
            return PinterestFetcher()
        else:
            return GenericFetcher()

    def add_post(self):
        url = self.url_input.text().strip()
        if not url:
            return
        group = self.group_input.currentText()
        fetcher = self.detect_fetcher(url)
        try:
            post = fetcher.fetch(url)
            post.group = group
            self.posts.append(post)
        except Exception as e:
            print(f"{fetcher} fetch error: {e}")
            return
        if group and group not in self.groups:
            self.groups.append(group)
            self.group_list.addItem(group)
            self.group_input.addItem(group)
        storage.posts = self.posts
        storage.groups = self.groups
        storage.save()
        self.url_input.clear()
        self.update_display()

    def add_group(self):
        new_group = self.new_group_input.text().strip()
        if new_group and new_group not in self.groups:
            self.groups.append(new_group)
            self.group_list.addItem(new_group)
            self.group_input.addItem(new_group)
            storage.groups = self.groups
            storage.save()
            self.new_group_input.clear()

    def update_display(self):
        filter_text = self.filter_input.text().lower()
        sort_by = self.sort_box.currentText().lower()
        selected_group_item = self.group_list.currentItem()
        selected_group = selected_group_item.text() if selected_group_item else "All"

        filtered = []
        for p in self.posts:
            if selected_group != "All" and p.group != selected_group:
                continue
            if (filter_text in p.title.lower() or
                filter_text in p.platform.lower() or
                any(filter_text in tag.lower() for tag in p.tags) or
                filter_text in p.group.lower()):
                filtered.append(p)

        if sort_by == "title":
            filtered.sort(key=lambda x: x.title.lower())
        elif sort_by == "platform":
            filtered.sort(key=lambda x: x.platform.lower())
        elif sort_by == "group":
            filtered.sort(key=lambda x: x.group.lower())

        self.table.setRowCount(len(filtered))
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["Image", "Title", "Platform", "Tags", "Description", "URL", "Group", "Delete"])


        for i, post in enumerate(filtered):
            if post.images:
            
                loader = ImageLoader(i, post.images[0])
                loader_thread = QtCore.QThread()
                loader.moveToThread(loader_thread)
                loader.finished.connect(self.on_image_loaded)
                loader.error.connect(self.on_image_error)
                loader_thread.started.connect(loader.load)
                loader_thread.start()
                # Keep references to prevent GC
                if not hasattr(self, '_loader_threads'):
                    self._loader_threads = []
                self._loader_threads.append((loader_thread, loader))
            
                #threading.Thread(target=self.load_image_async, args=(i, post.images[0]), daemon=True).start()
            else:
                self.table.setItem(i, 0, QtWidgets.QTableWidgetItem("No Image"))

            self.table.setItem(i, 1, QtWidgets.QTableWidgetItem(post.title))
            self.table.setItem(i, 2, QtWidgets.QTableWidgetItem(post.platform))
            self.table.setItem(i, 3, QtWidgets.QTableWidgetItem(", ".join(post.tags)))
            self.table.setItem(i, 4, QtWidgets.QTableWidgetItem(post.description[:100]))
            self.table.setItem(i, 5, QtWidgets.QTableWidgetItem(post.url))
            self.table.setItem(i, 6, QtWidgets.QTableWidgetItem(post.group))

            delete_btn = QtWidgets.QPushButton("Delete")
            delete_btn.clicked.connect(lambda _, url=post.url: self.delete_post(url))
            self.table.setCellWidget(i, 7, delete_btn)
            
            self.table.setRowHeight(i,120)
            for col in range(self.table.columnCount()):
                item = self.table.item(i, col)
                if item:
                    item.setTextAlignment(QtCore.Qt.AlignCenter)
            
        self.table.setColumnWidth(0, 160)
        self.table.setColumnWidth(1, 200)
        self.table.setColumnWidth(2, 90)
        self.table.setColumnWidth(3, 120)
        self.table.setColumnWidth(4, 200)
        self.table.setColumnWidth(5, 100)
        self.table.setColumnWidth(6, 100)
        self.table.setColumnWidth(7, 40)

    def delete_post(self, url):
        self.posts = [p for p in self.posts if p.url != url]
        storage.posts = self.posts
        storage.save()
        self.update_display()

    def export_json(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export Posts JSON", "", "JSON Files (*.json)")
        if path:
            data = {
                "posts": [asdict(p) for p in self.posts],
                "groups": self.groups,
            }
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)

    def import_json(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Import Posts JSON", "", "JSON Files (*.json)")
        if path:
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                posts_data = data.get("posts", [])
                groups_data = data.get("groups", [])
                self.posts = [PostData(**p) for p in posts_data]
                self.groups = groups_data

                storage.posts = self.posts
                storage.groups = self.groups
                storage.save()

                self.group_list.clear()
                self.group_list.addItem("All")
                for g in self.groups:
                    self.group_list.addItem(g)

                self.group_input.clear()
                self.group_input.addItem("")
                self.group_input.addItems(self.groups)

                self.update_display()
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "Import Error", f"Failed to import: {e}")

def main(self):
    parser = argparse.ArgumentParser()
    parser.add_argument('--storage', choices=['json', 'sqlite'], default='json')
    parser.add_argument('--fetch', type=str, help='Fetch URL and save to DB')
    parser.add_argument('--gui', action='store_true', help='Launch GUI')
    args = parser.parse_args()
    
    storage: StorageInterface
    if args.storage == 'json':
        storage = JSONStorage()
    else:
        storage = SQLiteStorage()
    
    if args.fetch:
        fetcher = self.detect_fetcher(self.url_input.text())
        post = fetcher.fetch(args.fetch)
        if post:
            storage.save_post(post)
            print("Saved post:", post.title)
        else:
            print("Failed to fetch post.")
    app = QtWidgets.QApplication(sys.argv)
    w = PostApp(storage)
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
