# lipanim_tk.py
import os, json, string, time, threading
from tkinter import Tk, Frame, Label, Entry, Button, Listbox, END, SINGLE, filedialog, Scrollbar, RIGHT, Y, LEFT, BOTH, StringVar
from PIL import Image, ImageTk
from moviepy.editor import ImageClip, concatenate_videoclips

LETTERS = list(string.ascii_uppercase)

def load_letter_map_from_dir(folder):
    m={}
    if not (folder and os.path.isdir(folder)): return m
    priority={}
    def assign(letter,path,p):
        if letter not in LETTERS: return
        prev=priority.get(letter,10_000)
        if p<=prev:
            m[letter]=path; priority[letter]=p
    for fn in os.listdir(folder):
        path=os.path.join(folder,fn); name,ext=os.path.splitext(fn)
        if ext.lower() not in (".png",".jpg",".jpeg",".webp",".bmp"): continue
        base=name.strip(); lower=base.lower()
        if lower in ("fallback","pause"): continue
        if len(base)==1 and base.upper() in LETTERS:
            assign(base.upper(),path,0); continue
        if "-" in base:
            tokens=[t.strip() for t in base.replace(" ","").split("-") if t.strip()]
            for t in tokens:
                tu=t.upper();
                if len(tu)==1 and tu in LETTERS: assign(tu,path,5)
            continue
        # multi-letter tokens ignored here
    return m

def valid_img(p): return bool(p) and os.path.isfile(p)

def build_sequence(text, letter_map, dur_ms, gap_ms, fallback=None):
    seq=[]
    for ch in text:
        if ch==" ":
            if gap_ms>0: seq.append({"char":" ","img":None,"ms":gap_ms})
            continue
        key=ch.upper()
        img=letter_map.get(key) or (fallback if valid_img(fallback) else None)
        if img: seq.append({"char":ch,"img":img,"ms":dur_ms})
    return seq

def export_json(seq, path):
    with open(path,"w",encoding="utf-8") as f:
        json.dump({"frames":seq}, f, ensure_ascii=False, indent=2)

def export_mp4(seq, path, fps, crf, preset, bg=(0,0,0,0)):
    imgs=[s for s in seq if s["img"]]
    if not imgs: raise RuntimeError("Sequência vazia.")
    from PIL import Image as PILImage
    w,h = PILImage.open(imgs[0]["img"]).size
    clips=[]; tmp_blanks=[]
    for f in seq:
        if f["img"] is None:
            im=PILImage.new("RGBA",(w,h),bg); tmp=os.path.join(os.path.dirname(path) or ".", f"__blank_{f['ms']}.png")
            im.save(tmp); tmp_blanks.append(tmp)
            clips.append(ImageClip(tmp).set_duration(max(f["ms"],1)/1000.0))
        else:
            c=ImageClip(f["img"]).set_duration(max(f["ms"],1)/1000.0)
            if c.w!=w or c.h!=h: c=c.resize(newsize=(w,h))
            clips.append(c)
    video=concatenate_videoclips(clips, method="compose").set_fps(fps)
    video.write_videofile(path, codec="libx264", audio=False, fps=fps, preset=preset, ffmpeg_params=["-crf", str(crf), "-pix_fmt", "yuv420p"])
    video.close()
    for p in tmp_blanks:
        try: os.remove(p)
        except: pass

# ---------------- UI (Tkinter) ----------------
class App:
    def __init__(self, root):
        self.root=root; root.title("Face Sequencer Minimal (Tk)")
        self.letter_map={}
        self.sequence=[]
        self.preview_stop=False
        self.preview_size=None
        top=Frame(root); top.pack(fill="x", padx=6, pady=4)

        self.dir_var=StringVar(); Label(top,text="Folder:").pack(side=LEFT)
        Entry(top,textvariable=self.dir_var,width=50).pack(side=LEFT, padx=4)
        Button(top,text="Browse",command=self.browse_dir).pack(side=LEFT)
        Button(top,text="Fill from folder",command=self.fill_from_folder).pack(side=LEFT, padx=4)

        self.fallback_var=StringVar(); Label(top,text="Fallback:").pack(side=LEFT, padx=(10,2))
        Entry(top,textvariable=self.fallback_var,width=24).pack(side=LEFT)
        Button(top,text="Choose",command=self.choose_fallback).pack(side=LEFT, padx=2)

        row2=Frame(root); row2.pack(fill="x", padx=6, pady=4)
        self.text_var=StringVar(); Label(row2,text="Text:").pack(side=LEFT)
        Entry(row2,textvariable=self.text_var,width=60).pack(side=LEFT, padx=4)

        self.ms_var=StringVar(value="80")
        self.gap_var=StringVar(value="120")
        self.fps_var=StringVar(value="30")
        self.crf_var=StringVar(value="14")
        self.preset_var=StringVar(value="slow")

        for lab,var,width in [("ms/letter:",self.ms_var,6),("ms space:",self.gap_var,6),
                              ("FPS:",self.fps_var,4),("CRF:",self.crf_var,4),("Preset:",self.preset_var,8)]:
            Label(row2,text=lab).pack(side=LEFT, padx=2)
            Entry(row2,textvariable=var,width=width).pack(side=LEFT)

        row3=Frame(root); row3.pack(fill="x", padx=6, pady=4)
        Button(row3,text="Build Sequence",command=self.build).pack(side=LEFT)
        Button(row3,text="Preview",command=self.preview).pack(side=LEFT, padx=2)
        Button(row3,text="Remove Frame",command=self.remove).pack(side=LEFT, padx=2)
        Button(row3,text="Up",command=lambda:self.move(-1)).pack(side=LEFT, padx=2)
        Button(row3,text="Down",command=lambda:self.move(+1)).pack(side=LEFT, padx=2)
        Label(row3,text="frame ms:").pack(side=LEFT, padx=(10,2))
        self.editms_var=StringVar(); Entry(row3,textvariable=self.editms_var,width=6).pack(side=LEFT)
        Button(row3,text="Apply",command=self.apply_ms).pack(side=LEFT, padx=2)
        Button(row3,text="Export JSON",command=self.save_json).pack(side=LEFT, padx=8)
        Button(row3,text="Export MP4",command=self.save_mp4).pack(side=LEFT)

        mid=Frame(root); mid.pack(fill=BOTH, expand=True, padx=6, pady=4)
        Label(mid,text="Sequence:").pack(anchor="w")
        lst_frame=Frame(mid); lst_frame.pack(fill=BOTH, expand=True)
        self.listbox=Listbox(lst_frame, selectmode=SINGLE)
        self.listbox.pack(side=LEFT, fill=BOTH, expand=True)
        sb=Scrollbar(lst_frame, orient="vertical", command=self.listbox.yview); sb.pack(side=RIGHT, fill=Y)
        self.listbox.config(yscrollcommand=sb.set)
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        pv=Frame(root); pv.pack(fill=BOTH, padx=6, pady=4)
        self.preview_label=Label(pv, text="(preview)")
        self.preview_label.pack()

    def browse_dir(self):
        d=filedialog.askdirectory()
        if d: self.dir_var.set(d)

    def choose_fallback(self):
        p=filedialog.askopenfilename(filetypes=[("Images","*.png;*.jpg;*.jpeg;*.webp;*.bmp")])
        if p: self.fallback_var.set(p)

    def fill_from_folder(self):
        self.letter_map = load_letter_map_from_dir(self.dir_var.get().strip())
        self.info(f"Mapped {len(self.letter_map)} letters.")

    def build(self):
        try:
            dur=int(self.ms_var.get() or "80")
            gap=int(self.gap_var.get() or "120")
            fb=self.fallback_var.get().strip() or None
            self.sequence = build_sequence(self.text_var.get(), self.letter_map, dur, gap, fb)
            self.refresh_list()
        except Exception as e:
            self.info(f"Build error: {e}")

    def refresh_list(self):
        self.listbox.delete(0, END)
        for i,f in enumerate(self.sequence):
            self.listbox.insert(END, f"{i:03d} | '{f['char']}' | {os.path.basename(f['img']) if f['img'] else '[PAUSE]'} | {f['ms']}ms")

    def on_select(self, _evt):
        i=self.current_index()
        if i is not None: self.editms_var.set(str(self.sequence[i]["ms"]))

    def current_index(self):
        s=self.listbox.curselection()
        return s[0] if s else None

    def apply_ms(self):
        i=self.current_index()
        if i is None: return
        try:
            self.sequence[i]["ms"]=max(1,int(self.editms_var.get() or self.sequence[i]["ms"]))
            self.refresh_list(); self.listbox.selection_set(i)
        except Exception as e:
            self.info(f"Apply error: {e}")

    def remove(self):
        i=self.current_index()
        if i is None: return
        del self.sequence[i]; self.refresh_list()

    def move(self, delta):
        i=self.current_index()
        if i is None: return
        j=i+delta
        if 0<=j<len(self.sequence):
            self.sequence[i],self.sequence[j]=self.sequence[j],self.sequence[i]
            self.refresh_list(); self.listbox.selection_set(j)

    def preview(self):
        if not self.sequence: self.info("Build the sequence first."); return
        self.preview_stop=False
        threading.Thread(target=self._run_preview, daemon=True).start()

    def _run_preview(self):
        for f in self.sequence:
            if self.preview_stop: break
            if f["img"] is None:
                time.sleep(max(f["ms"],1)/1000.0); continue
            im=Image.open(f["img"]).convert("RGBA")
            if self.preview_size is None: self.preview_size=im.size
            else: im=im.resize(self.preview_size, Image.LANCZOS)
            photo=ImageTk.PhotoImage(im)
            def update(): self.preview_label.config(image=photo); self.preview_label.image=photo
            self.root.after(0, update)
            time.sleep(max(f["ms"],1)/1000.0)

    def save_json(self):
        if not self.sequence: self.info("Nothing to export."); return
        p=filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON","*.json")])
        if p:
            try: export_json(self.sequence,p); self.info("JSON saved.")
            except Exception as e: self.info(f"JSON error: {e}")

    def save_mp4(self):
        if not self.sequence: self.info("Nothing to export."); return
        p=filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4","*.mp4")])
        if p:
            try:
                fps=max(1,int(self.fps_var.get() or "30"))
                crf=min(30,max(0,int(self.crf_var.get() or "14")))
                preset=self.preset_var.get() or "slow"
                export_mp4(self.sequence,p,fps,crf,preset)
                self.info("MP4 exported.")
            except Exception as e:
                self.info(f"MP4 error: {e}")

    def info(self, msg):
        self.root.title(f"Face Sequencer Minimal (Tk) — {msg}")

if __name__=="__main__":
    root=Tk()
    App(root)
    root.mainloop()
