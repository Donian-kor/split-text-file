import argparse
import re
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

DEFAULT_CHUNK_SIZE = 100 * 1024  # 100 KB

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    TkinterDnD = tk.Tk
    DND_FILES = None


def split_text_file(input_path: Path, chunk_size: int = DEFAULT_CHUNK_SIZE, output_dir: Path | None = None) -> list[Path]:
    input_path = input_path.resolve()
    if not input_path.exists() or not input_path.is_file():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {input_path}")

    parent = output_dir.resolve() if output_dir else input_path.parent
    parent.mkdir(parents=True, exist_ok=True)

    output_files: list[Path] = []
    base_name = input_path.stem
    suffix = input_path.suffix or ".txt"

    with input_path.open("rb") as source:
        chunk_index = 1
        current_bytes = bytearray()

        for line in source:
            if len(current_bytes) + len(line) > chunk_size:
                if current_bytes:
                    output_path = parent / f"{base_name}_{chunk_index:02d}{suffix}"
                    output_path.write_bytes(current_bytes)
                    output_files.append(output_path)
                    chunk_index += 1
                    current_bytes = bytearray()

                if len(line) > chunk_size:
                    start = 0
                    while start < len(line):
                        end = min(start + chunk_size, len(line))
                        output_path = parent / f"{base_name}_{chunk_index:02d}{suffix}"
                        output_path.write_bytes(line[start:end])
                        output_files.append(output_path)
                        chunk_index += 1
                        start = end
                    continue

            current_bytes.extend(line)

        if current_bytes:
            output_path = parent / f"{base_name}_{chunk_index:02d}{suffix}"
            output_path.write_bytes(current_bytes)
            output_files.append(output_path)

    return output_files


def parse_drag_files(data: str) -> list[Path]:
    if not data:
        return []

    paths: list[Path] = []
    for match in re.finditer(r"\{([^}]+)\}|([^\s]+)", data):
        path_text = match.group(1) or match.group(2)
        if not path_text:
            continue
        if path_text.startswith("file://"):
            path_text = path_text[7:]
            if path_text.startswith("/") and ":" in path_text[1:3]:
                path_text = path_text.lstrip("/")
        paths.append(Path(path_text))

    return paths


def run_gui() -> None:
    class SplitTextGUI(TkinterDnD.Tk):
        def __init__(self):
            super().__init__()
            self.title("텍스트 파일 분할기 ver.260622")
            self.geometry("700x450")
            self.minsize(660, 380)
            self.resizable(True, True)
            self.selected_path: Path | None = None
            self.output_dir: Path | None = None

            self.file_path_var = tk.StringVar()
            self.output_dir_var = tk.StringVar()
            self.status_var = tk.StringVar(value="텍스트 파일을 드래그하거나 버튼으로 선택하세요.")
            self.size_var = tk.StringVar(value="100")

            self._build_widgets()

        def _build_widgets(self) -> None:
            style = ttk.Style(self)
            style.theme_use("clam")
            # 버튼 색상, 글자색, 모서리, 여백 등을 여기서 설정합니다.
            style.configure("Accent.TButton", foreground="white", background="#000100", borderwidth=0, padding=8)
            style.map("Accent.TButton", background=[("active", "#2563eb"), ("pressed", "#1d4ed8")])
            # 굵은 레이블 폰트 및 색상을 여기서 바꿀 수 있습니다.
            style.configure("Bold.TLabel", font=("Malgun Gothic", 12, "bold"), foreground="#1f2937")
            # 일반 레이블 폰트 및 색상을 여기서 바꿀 수 있습니다.
            style.configure("Normal.TLabel", font=("Malgun Gothic", 9), foreground="#374151")

            self.button_width = 18  # 버튼 너비를 여기서 조절하세요.
            # 전체 GUI 여백과 크기를 조정하려면 padding 값을 바꿔주세요.
            frame = ttk.Frame(self, padding=14)
            frame.pack(fill="both", expand=True)

            drop_frame = ttk.Frame(frame, relief="ridge", borderwidth=2)
            drop_frame.pack(fill="both", expand=True, pady=(0, 12))

            # 드래그 영역 배경색, 글자색, 글꼴, 여백을 여기서 수정합니다.
            drop_label = tk.Label(
                drop_frame,
                text="▶ 여기에 분할하려는 text 파일을 drag & drop 하세요.\n▶ 분할파일 저장폴더를 선택하세요. \n▶ 분할시작 버튼 왼쪽 입력칸에 원하는 KB를 입력하고, 분할시작 버튼클릭. ",
                bg="#eef2ff",
                fg="#c11108",
                font=("Malgun Gothic", 13, "bold"),
                pady=30,
                borderwidth=0,
                anchor="center",      # 라벨 내부에서 왼쪽 정렬
                justify="left"   # 여러 줄 텍스트 왼쪽 정렬
            )
            drop_label.pack(fill="both", expand=True)

            if DND_FILES is not None:
                drop_label.drop_target_register(DND_FILES)
                drop_label.dnd_bind("<<Drop>>", self._on_drop)
            else:
                drop_label.config(text="이 환경에서는 드래그 앤 드랍을 사용할 수 없습니다. 버튼으로 파일을 선택하세요.")

            entry_frame = ttk.Frame(frame)
            entry_frame.pack(fill="x", pady=(0, 10))
            entry_frame.columnconfigure(0, weight=1)
            entry_frame.columnconfigure(1, weight=0)
            entry_frame.columnconfigure(2, weight=0)

            # 파일 선택 입력창을 왼쪽으로 넓게 배치합니다.
            file_entry = ttk.Entry(entry_frame, textvariable=self.file_path_var, state="readonly")
            file_entry.grid(row=0, column=0, sticky="ew", pady=(0, 4))
            choose_button = ttk.Button(entry_frame, text="파일 선택", style="Accent.TButton", width=self.button_width, command=self._choose_file)
            choose_button.grid(row=0, column=1, padx=(10, 0), pady=(0, 4), sticky="e")

            # 저장 위치 입력창을 왼쪽으로 넓게 배치합니다.
            output_entry = ttk.Entry(entry_frame, textvariable=self.output_dir_var, state="readonly")
            output_entry.grid(row=1, column=0, sticky="ew", pady=(0, 4))
            choose_dir_button = ttk.Button(entry_frame, text="저장 위치 선택", style="Accent.TButton", width=self.button_width, command=self._choose_output_dir)
            choose_dir_button.grid(row=1, column=1, padx=(10, 0), pady=(0, 4), sticky="e")

            # 분할 크기 입력창과 분할 시작 버튼을 한 줄에 배치합니다.
            digits_cmd = self.register(self._validate_digits)
            size_entry = ttk.Entry(entry_frame, textvariable=self.size_var, width=10, validate="key", validatecommand=(digits_cmd, "%P"))
            size_entry.grid(row=2, column=0, sticky="e", pady=(12, 4))
            split_button = ttk.Button(entry_frame, text="분할 시작", style="Accent.TButton", width=self.button_width, command=self._split_file)
            split_button.grid(row=2, column=1, pady=(12, 4), padx=(10, 0), sticky="e")

            # 상태 메시지를 가운데 정렬합니다.
            ttk.Label(frame, textvariable=self.status_var, style="Normal.TLabel", wraplength=620, anchor="center", justify="center").pack(fill="x", pady=(8, 0))

        def _validate_digits(self, value: str) -> bool:
            # 분할 크기 입력창에 숫자만 입력되도록 검증합니다.
            return value.isdigit() or value == ""

        def _choose_file(self) -> None:
            file_path = filedialog.askopenfilename(
                title="텍스트 파일 선택",
                filetypes=[("Text Files", "*.txt"), ("All Files", "*")],
            )
            if file_path:
                self._set_file(Path(file_path))

        def _choose_output_dir(self) -> None:
            folder_path = filedialog.askdirectory(
                title="저장 위치 선택",
            )
            if folder_path:
                self.output_dir = Path(folder_path)
                self.output_dir_var.set(str(self.output_dir))
                self.status_var.set("저장 위치가 설정되었습니다. 분할 시작을 눌러주세요.")

        def _on_drop(self, event: tk.Event) -> None:
            try:
                dropped_paths = parse_drag_files(event.data)
                if not dropped_paths:
                    raise ValueError("올바른 파일이 드랍되지 않았습니다.")
                self._set_file(dropped_paths[0])
            except Exception as exc:
                messagebox.showerror("오류", f"드랍 중 오류가 발생했습니다: {exc}")

        def _set_file(self, path: Path) -> None:
            if not path.exists() or not path.is_file():
                messagebox.showerror("오류", "유효한 텍스트 파일을 선택하세요.")
                return
            self.selected_path = path
            self.file_path_var.set(str(path))
            if not self.output_dir:
                self.output_dir = path.parent
                self.output_dir_var.set(str(self.output_dir))
            self.status_var.set("파일이 선택되었습니다. 분할 크기를 확인하고 분할 시작을 눌러주세요.")

        def _split_file(self) -> None:
            if self.selected_path is None:
                messagebox.showwarning("경고", "먼저 분할할 텍스트 파일을 선택하세요.")
                return

            try:
                chunk_size = int(self.size_var.get())
                if chunk_size < 1:
                    raise ValueError("분할 크기는 1KB 이상이어야 합니다.")
            except ValueError:
                messagebox.showerror("오류", "분할 크기는 자연수로 입력하세요.")
                return

            try:
                output_files = split_text_file(self.selected_path, chunk_size * 1024, self.output_dir)
                self.status_var.set(f"분할 완료: {len(output_files)}개 파일 생성됨")
                messagebox.showinfo("완료", f"분할이 완료되었습니다.\n생성된 파일 수: {len(output_files)}")
            except Exception as exc:
                messagebox.showerror("오류", str(exc))
                self.status_var.set(f"오류 발생: {exc}")

    app = SplitTextGUI()
    app.mainloop()


def main() -> None:
    parser = argparse.ArgumentParser(description="텍스트 파일을 100KB 단위로 자동 분할합니다.")
    parser.add_argument("input", nargs="?", help="분할할 텍스트 파일 경로")
    parser.add_argument("-s", "--size", type=int, default=100, help="분할 단위 KB (기본값: 100)")
    args = parser.parse_args()

    if args.input is None:
        run_gui()
        return

    input_path = Path(args.input)
    chunk_size = max(1, args.size) * 1024

    try:
        output_files = split_text_file(input_path, chunk_size)
        print(f"분할 완료: 총 {len(output_files)}개 파일 생성")
        for output in output_files:
            print(f"  - {output}")
    except Exception as exc:
        print(f"오류: {exc}")


if __name__ == "__main__":
    main()
