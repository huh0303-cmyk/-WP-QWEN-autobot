from __future__ import annotations
import json, os, shutil, subprocess, sys, threading, webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, scrolledtext

APP_NAME="LondonProjectGPT"
CONTROL_URL="https://control.korea365.org"

def find_repo() -> Path:
    env=os.environ.get("LONDON_PROJECT_ROOT","").strip()
    candidates=[]
    if env: candidates.append(Path(env))
    home=Path.home()
    candidates += [home/"Documents"/"LondonProject", home/"Documents"/"-WP-QWEN-autobot"]
    one=home/"OneDrive"
    if one.exists():
        candidates += [p for p in one.glob("**/-WP-QWEN-autobot") if p.is_dir()][:3]
    for p in candidates:
        if (p/"scripts"/"tistory_local_runner.py").exists():
            return p.resolve()
    raise FileNotFoundError("London Project 저장소를 찾지 못했습니다. LONDON_PROJECT_ROOT 환경변수를 설정하세요.")

def python_cmd():
    exe=shutil.which("python") or shutil.which("python3")
    if exe: return [exe]
    py=shutil.which("py")
    if py: return [py,"-3"]
    raise FileNotFoundError("Python을 찾지 못했습니다.")

def load_env(repo:Path):
    env=os.environ.copy()
    f=repo/".env"
    if f.exists():
        for raw in f.read_text(encoding="utf-8").splitlines():
            line=raw.strip()
            if not line or line.startswith("#") or "=" not in line: continue
            k,v=line.split("=",1)
            if k.strip() not in env:
                env[k.strip()]=v.strip().strip('"').strip("'")
    return env

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("780x560")
        self.repo=None
        try: self.repo=find_repo()
        except Exception as e: self.repo_error=str(e)
        self._ui(); self.local_status()

    def _ui(self):
        tk.Label(self,text="런던프로젝트GPT",font=("Segoe UI",20,"bold")).pack(pady=(12,4))
        tk.Label(self,text="Simple · Stable · No-New-Cost · Local Browser Agent",font=("Segoe UI",10)).pack()
        top=tk.Frame(self); top.pack(fill="x",padx=14,pady=10)
        tk.Button(top,text="Control Korea365 열기",command=lambda:webbrowser.open(CONTROL_URL),width=22).pack(side="left",padx=4)
        tk.Button(top,text="로컬 상태 확인",command=self.local_status,width=18).pack(side="left",padx=4)
        tk.Button(top,text="Aside 실행",command=self.launch_aside,width=14).pack(side="left",padx=4)

        nav=tk.LabelFrame(self,text="Naver Blog 3 · 로컬 로그인 세션",padx=8,pady=8); nav.pack(fill="x",padx=14,pady=6)
        tk.Label(nav,text="site_id").pack(side="left")
        self.naver_id=tk.Entry(nav,width=24); self.naver_id.pack(side="left",padx=6)
        tk.Button(nav,text="로그인",command=lambda:self.run_visible(["scripts/naver_blog_local_runner.py","login","--site-id",self.naver_id.get().strip()])).pack(side="left",padx=3)
        tk.Button(nav,text="1건 실행",command=self.naver_run).pack(side="left",padx=3)

        tis=tk.LabelFrame(self,text="Tistory 5 · 로컬 로그인 세션",padx=8,pady=8); tis.pack(fill="x",padx=14,pady=6)
        tk.Button(tis,text="로그인",command=lambda:self.run_visible(["scripts/tistory_local_runner.py","login"])).pack(side="left",padx=3)
        tk.Button(tis,text="큐 상태",command=lambda:self.run_capture(["scripts/tistory_local_runner.py","status"])).pack(side="left",padx=3)
        tk.Button(tis,text="1건 실행",command=self.tistory_run).pack(side="left",padx=3)

        tk.Label(self,text="실행/상태 로그 (비밀번호·토큰은 표시하지 않음)",anchor="w").pack(fill="x",padx=14,pady=(10,2))
        self.log=scrolledtext.ScrolledText(self,height=18,font=("Consolas",9)); self.log.pack(fill="both",expand=True,padx=14,pady=(0,12))

    def write(self,msg):
        self.log.insert("end",str(msg)+"\n"); self.log.see("end")

    def require_repo(self):
        if self.repo: return self.repo
        messagebox.showerror(APP_NAME,getattr(self,"repo_error","저장소를 찾지 못했습니다.")); return None

    def local_status(self):
        self.log.delete("1.0","end")
        self.write("=== LondonProjectGPT Local Agent ===")
        self.write("Repo: "+(str(self.repo) if self.repo else "NOT FOUND"))
        aside=Path(os.environ.get("ProgramFiles",r"C:\Program Files"))/"Aside"/"Application"/"Aside.exe"
        self.write("Aside: "+("OK" if aside.exists() else "NOT FOUND"))
        self.write("Python: "+str(shutil.which("python") or shutil.which("py") or "NOT FOUND"))
        if self.repo:
            self.write("Tistory runner: "+str((self.repo/"scripts/tistory_local_runner.py").exists()))
            self.write("Naver runner: "+str((self.repo/"scripts/naver_blog_local_runner.py").exists()))
            self.write(".env: "+("present (values hidden)" if (self.repo/".env").exists() else "missing"))

    def launch_aside(self):
        aside=Path(os.environ.get("ProgramFiles",r"C:\Program Files"))/"Aside"/"Application"/"Aside.exe"
        if not aside.exists(): return messagebox.showerror(APP_NAME,"Aside.exe를 찾지 못했습니다.")
        subprocess.Popen([str(aside)])

    def base_command(self,args):
        repo=self.require_repo()
        if not repo: return None,None,None
        return python_cmd()+[str(repo/args[0])]+args[1:], repo, load_env(repo)

    def run_visible(self,args):
        if not args[-1] and "--site-id" in args: return messagebox.showwarning(APP_NAME,"Naver site_id를 입력하세요.")
        try:
            cmd,repo,env=self.base_command(args)
            if not cmd:return
            subprocess.Popen(cmd,cwd=repo,env=env,creationflags=getattr(subprocess,"CREATE_NEW_CONSOLE",0))
            self.write("실행 시작: "+" ".join(args))
        except Exception as e: messagebox.showerror(APP_NAME,str(e))

    def run_capture(self,args):
        def work():
            try:
                cmd,repo,env=self.base_command(args)
                if not cmd:return
                p=subprocess.run(cmd,cwd=repo,env=env,text=True,capture_output=True,timeout=120,encoding="utf-8",errors="replace")
                self.after(0,lambda:self.write((p.stdout or p.stderr or f"exit={p.returncode}")[-12000:]))
            except Exception as e:self.after(0,lambda:self.write("ERROR: "+str(e)))
        threading.Thread(target=work,daemon=True).start()

    def tistory_run(self):
        if messagebox.askyesno(APP_NAME,"Tistory ready 큐에서 최대 1건만 실행합니다. 로그인/CAPTCHA가 나오면 중단(HOLD)하세요. 실행할까요?"):
            self.run_visible(["scripts/tistory_local_runner.py","run","--max-jobs","1","--gap-seconds","0"])

    def naver_run(self):
        sid=self.naver_id.get().strip()
        if not sid:return messagebox.showwarning(APP_NAME,"Naver site_id를 입력하세요.")
        if messagebox.askyesno(APP_NAME,f"{sid}의 ready 큐에서 최대 1건만 실행합니다. 로그인/CAPTCHA가 나오면 중단하세요. 실행할까요?"):
            self.run_visible(["scripts/naver_blog_local_runner.py","run","--site-id",sid,"--max-jobs","1"])

if __name__=="__main__":
    App().mainloop()
