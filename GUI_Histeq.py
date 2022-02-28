import os
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import numpy as np
from PIL import Image
from scipy import ndimage
from io import BytesIO
import datetime

"""
-----Change Log-----
0.1  - Newly created
0.2a - Add <Delete RAW> checkbox ; Add <check_time>
0.2b - Minor changes to GUI (add separator, change btn label)
0.3  - Revise image w,h detection from based on filename to actual size
TODO: ^ for ING only, how to for RAW???
--------------------
"""
path: str = "./"


def check_time():
    #return datetime.datetime.now() < datetime.datetime.strptime('14-3-2021', '%d-%m-%Y')
    return 1


def check_model(name):
    name_split = name.split("_")
    img_name = name_split[2]
    if "D50A1" in img_name or "MODL50on" in img_name:
        w, h = 4224, 3176
    else:
        w, h = 4224, 3024
    return w, h


def ing2raw(file_name):
    with open(path + '/' + file_name, 'rb') as ing_f:
        ing_f.seek(56)
        im = Image.open(BytesIO(ing_f.read()))
    im_np = np.array(im)
    w_t, h_t = im_np.shape
    w_t = int(w_t / 5)
    h = h_t * 2
    w = w_t * 2
    r = im_np[:w_t, :].transpose()
    gr = im_np[w_t:w_t * 2, :].transpose()
    gb = im_np[w_t * 2:w_t * 3, :].transpose()
    b = im_np[w_t * 3:w_t * 4, :].transpose()
    noise = im_np[w_t * 4:, :].transpose()
    raw = np.zeros((h_t * 2, int(w_t * 2 * 5 / 4)), dtype=np.uint8)
    raw[::2, ::5] = r[:, ::2]
    raw[::2, 2::5] = r[:, 1::2]
    raw[::2, 1::5] = gr[:, ::2]
    raw[::2, 3::5] = gr[:, 1::2]
    raw[1::2, ::5] = gb[:, ::2]
    raw[1::2, 2::5] = gb[:, 1::2]
    raw[1::2, 1::5] = b[:, ::2]
    raw[1::2, 3::5] = b[:, 1::2]
    raw[:h_t, 4::5] = noise[:, ::2]
    raw[h_t:, 4::5] = noise[:, 1::2]
    return raw, w, h


def bayer2raw(bayer, w, h):
    global path
    bayer2 = path + '/' + bayer
    filesize = int(w * h * 5 / 4)
    a = np.fromfile(bayer2, dtype=np.uint8, count=filesize)
    a5 = a[4:filesize:5]
    a1 = np.uint16(a[0:filesize:5]) * 4 + ((a5 & (3 << 0)) >> 0)
    a2 = np.uint16(a[1:filesize:5]) * 4 + ((a5 & (3 << 2)) >> 2)
    a3 = np.uint16(a[2:filesize:5]) * 4 + ((a5 & (3 << 4)) >> 4)
    a4 = np.uint16(a[3:filesize:5]) * 4 + ((a5 & (3 << 6)) >> 6)
    aa = np.vstack((a1, a2, a3, a4))
    raw = np.reshape(aa.T, [h, w])
    return raw


def histeq(im, nbr_bins=256):
    imhist, bins = np.histogram(im.flatten(), nbr_bins, density=True)  # get image histogram
    cdf = imhist.cumsum()  # cumulative distribution function
    cdf = 255 * cdf / cdf[-1]  # normalize
    im2 = np.interp(im.flatten(), bins[:-1], cdf)  # use linear interpolation of cdf to find new pixel values
    return im2.reshape(im.shape), cdf


def resize(img):
    global s_factor
    s_factor = int(en_factor.get()) / 100
    ow, oh = img.size
    nw = int(ow * s_factor)
    nh = int(oh * s_factor)
    img = img.resize([nw, nh], resample=Image.BILINEAR)
    return img


def browse():  # hit browse button & update path
    path = filedialog.askdirectory(initialdir='./')
    en_path.delete(0, tk.END)
    en_path.insert(0, path)


def load_bar_update(f_count, total):
    '''global f
    k = 100 * f_count / total
    f.set(k)
    main.update_idletasks()'''
    #messagebox.showinfo('Completed', 'Completed!', icon='info')
    return 0


def bt_f_ing2raw():
    global path, f
    path = en_path.get()
    files = [fi for fi in os.listdir(path) if (fi.endswith('.ing') or fi.endswith('.ING'))]
    f_count = 0
    for fi in files:
        raw, w, h = ing2raw(fi)
        raw.tofile(path + '/' + fi.split('.')[0] + '.raw')
        f_count += 1
        load_bar_update(f_count, len(files))


def bt_f_ing_hist():
    global path, f, s_factor, scale_check
    path = en_path.get()
    files = [fi for fi in os.listdir(path) if (fi.endswith('.ing') or fi.endswith('.ING'))]
    f_count = 0
    del_raw = del_raw_check.get()
    if check_time():
        for fi in files:
            rawi, w, h = ing2raw(fi)
            rawi.tofile(path + '/' + fi.split('.')[0] + '.raw')
            fi2 = fi.split('.')[0] + '.raw'
            #w, h = check_model(fi2)
            raw = bayer2raw(fi2, w, h)
            img = raw[0:h:2, 0:w:2]
            lsc_model = ndimage.uniform_filter(np.double(img), size=31, mode='nearest')
            lsc_model[lsc_model == 0] = 1e-10
            im_lsc = np.uint8(img / lsc_model * 128)
            im2, cdf = histeq(im_lsc)
            bmp_img = Image.fromarray(np.uint8(im2))
            if scale_check.get():
                bmp_img = resize(bmp_img)
            bmp_img.save(path + '/' + fi.split('.')[0] + '_HistEq_R.jpg', 'jpeg')
            if del_raw:
                os.remove(path + '/' + fi.split('.')[0] + '.raw')
            f_count += 1
            load_bar_update(f_count, len(files))


def bt_f_ing_heat():
    global path, f, s_factor, scale_check
    path = en_path.get()
    files = [fi for fi in os.listdir(path) if (fi.endswith('.ing') or fi.endswith('.ING'))]
    f_count = 0
    del_raw = del_raw_check.get()
    if check_time():
        for fi in files:
            rawi, w, h = ing2raw(fi)
            rawi.tofile(path + '/' + fi.split('.')[0] + '.raw')
            fi2 = fi.split('.')[0] + '.raw'
            #w, h = check_model(fi2)
            raw = bayer2raw(fi2, w, h)
            img = raw[0:h:2, 0:w:2]
            lsc_model = ndimage.uniform_filter(np.double(img), size=31, mode='nearest')
            lsc_model[lsc_model == 0] = 1e-10
            im_lsc = np.uint8(img / lsc_model * 128)
            im2, cdf = histeq(im_lsc)
            heat = plt.imshow(im2, cmap='viridis', interpolation='nearest')
            plt.colorbar(heat)
            plt.savefig(path + '/' + fi.split('.')[0] + '_Heatmap.jpg')
            if scale_check.get():
                bmp_img = resize(Image.open(path + '/' + fi.split('.')[0] + '_Heatmap.jpg'))
                bmp_img.save(path + '/' + fi.split('.')[0] + '_Heatmap.jpg', 'jpeg')
            if del_raw:
                os.remove(path + '/' + fi.split('.')[0] + '.raw')
            f_count += 1
            load_bar_update(f_count, len(files))


def bt_f_raw_hist():
    global path, f, s_factor, scale_check
    path = en_path.get()
    files = [fi for fi in os.listdir(path) if (fi.endswith('.raw') or fi.endswith('.RAW'))]
    f_count = 0
    del_raw = del_raw_check.get()
    if check_time():
        for fi in files:
            w, h = check_model(fi)
            raw = bayer2raw(fi, w, h)
            img = raw[0:h:2, 0:w:2]
            lsc_model = ndimage.uniform_filter(np.double(img), size=31, mode='nearest')
            lsc_model[lsc_model == 0] = 1e-10
            im_lsc = np.uint8(img / lsc_model * 128)
            im2, cdf = histeq(im_lsc)
            bmp_img = Image.fromarray(np.uint8(im2))
            if scale_check.get():
                bmp_img = resize(bmp_img)
            bmp_img.save(path + '/' + fi.split('.')[0] + '_HistEq_R.jpg', 'jpeg')
            if del_raw:
                os.remove(path + '/' + fi.split('.')[0] + '.raw')
            f_count += 1
            load_bar_update(f_count, len(files))


"""tkinter GUI"""

# GUI variables
C_BG = "#FFB900"
C_TXT = "#2c3e50"
C_TXT2 = "#fdfdfd"
C_BT1 = "#3498db"  # ing2raw
C_BT2 = "#3498db"  # hist_ing
C_BT3 = "#3498db"  # hist_raw
C_BT4 = "#3498db"  # browse

s_factor = 25  # default scale value 25%

main = tk.Tk()
main.configure(bg=C_BG)
main.title("HistEq plus 0.3")
main.geometry('%dx%d+%d+%d' % (422, 160, 417, 280))
main.resizable(False, False)
f = tk.DoubleVar()
scale_check = tk.IntVar()
del_raw_check = tk.IntVar()

lb_path = tk.Label(main, text='Folder:', height=2, bg=C_BG, fg=C_TXT).grid(row=0, sticky='E', padx=2)
ch_scale = tk.Checkbutton(main, text="Resize HistEq", height=2, variable=scale_check,
                          onvalue=True, offvalue=False, bg=C_BG, fg=C_TXT)
ch_scale.select()
ch_scale.grid(row=1, columnspan=2, padx=5)
ch_delraw = tk.Checkbutton(main, text="Delete RAW", height=2, variable=del_raw_check,
                           onvalue=True, offvalue=False, bg=C_BG, fg=C_TXT)
ch_delraw.deselect()
ch_delraw.grid(row=1, column=2, padx=5)
bt_ing2raw = tk.Button(main, text="ING to\nRAW", width=11, command=bt_f_ing2raw, bg=C_BT1, fg=C_TXT2) \
    .grid(row=3, column=1, padx=10)

en_path = tk.Entry(main, width=50)
en_path.insert(0, path)
en_path.grid(row=0, column=1, columnspan=3, sticky='E' + 'W', padx=0, ipadx=2, ipady=2)
lb_factor = tk.Label(main, text="Resize factor (%):", bg=C_BG, fg=C_TXT).grid(row=1, column=3,
                                                                             columnspan=1, padx=2, sticky='E')
bt_ing_hist = tk.Button(main, text="ING to\nHistEq & RAW", width=11,
                        command=bt_f_ing_hist, bg=C_BT2, fg=C_TXT2).grid(row=3, column=2, padx=10)

bt_path = tk.Button(main, text="Browse", command=browse, bg=C_BT4, fg=C_TXT2).grid(row=0, column=4, padx=2)
en_factor = tk.Entry(main, width=5)
en_factor.insert(0, str(s_factor))
en_factor.grid(row=1, column=4, sticky='W', padx=0, ipadx=2, ipady=2)
bt_raw_hist = tk.Button(main, text="RAW to\nHistEq", width=11,
                        command=bt_f_raw_hist, bg=C_BT3, fg=C_TXT2).grid(row=3, column=3, padx=10)

#load_bar = tk.ttk.Progressbar(main, variable=f, maximum=100, orient=tk.HORIZONTAL)
#load_bar.grid(row=4, columnspan=5, sticky='W'+'E'+'S', padx=4, pady=5)

tk.ttk.Separator(main, orient=tk.HORIZONTAL).grid(row=2, columnspan=5, sticky='W'+'E'+'N'+'S', padx=5, pady=5)

#tk.ttk.Separator(main, orient=tk.HORIZONTAL).grid(row=5, columnspan=5, sticky='W'+'E'+'N'+'S', padx=5, pady=5)
#lb_about = tk.Label(main, text='ING/RAW/HistEq image convert tool  |  Tony', height=1, font=('Segoe UI', '8'),
                    #bg=C_BG, fg=C_TXT).grid(row=5, columnspan=5, sticky='E', padx=2)
main.mainloop()
