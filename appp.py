from tkinter import *
from docxtpl import DocxTemplate
import tkinter.messagebox
from tkinter import ttk
import mysql.connector as sqltor
import datetime
import locale, os
from tkcalendar import Calendar, DateEntry
import sqlite3

import Table

# db =sqltor.connect(host = 'localhost',
#                    user = 'root' ,
#                    passwd = 'admin')

# cursor = db.cursor()
# cursor.execute("CREATE DATABASE IF NOT EXISTS BILLING_SOFT")
# cursor.execute('''USE BILLING_SOFT;
#                 CREATE TABLE IF NOT EXISTS INVOICE (invoice_number int primary key ,
#                 customer_name varchar(30),
#                 customer_id varchar(10),
#                 date date ,
#                 amount float(9,2))''')

#INSERTING DATA INTO DB
# def Save():
#     db =sqltor.connect(host = 'localhost',
#                    user = 'root' ,
#                    passwd = 'admin',
#                    database = 'BILLING_SOFT')
#     cursor = db.cursor()
#     cursor.execute('''INSERT INTO INVOICE VALUES
#               (%s,'%s','%s','%s','%s')'''%(invoice_number.get(),customer_name.get(),customer_id.get(),date_entry.get(),grandtotal.get()))
#     db.commit()
#     db.close()
    
#TO ADD TOTAL COST        
def Calc():
    subtotal.delete(0,END)
    grandtotal.delete(0,END)
    tax.delete(0,END)

    lst = []
    for i in range(20):
        if tree.exists(i):
            lst.append(i)
    p = []
    for i in lst:
        item = tree.item(str(i))
        rec = item['values'][4]
        p.append(rec)
    SUM = sum(p)
    p = []
    subtotal.insert(0,str(float(SUM)))
    tax.insert(0,str(SUM*0.18))
    grandtotal.insert(0,str(SUM*1.18))
    
#TO INSERT ITEMS
# def input_record():
#     global count
#     if id_entry.get()!= '' and UP_entry.get() != ''and QNTY_entry.get() != ''and ProductName_entry.get()!= '':
#         if id_entry.get().isdigit() and UP_entry.get().isdigit() and QNTY_entry.get().isdigit():          
#             prod = int(QNTY_entry.get()) * int(UP_entry.get())   
#             tree.insert('', index = END,iid = count,values=(id_entry.get(),
#                                             ProductName_entry.get(),
#                                             QNTY_entry.get(),
#                                             UP_entry.get(),
#                                             prod))

#             count += 1
#             id_entry.delete(0,END)
#             ProductName_entry.delete(0,END)
#             QNTY_entry.delete(0,END)
#             UP_entry.delete(0,END)
#         else:
#             tkinter.messagebox.showinfo("WARNING!!!!!!","Enter Valid Entries!! ")

#     else:
#         tkinter.messagebox.showinfo("WARNING.",  "Enter all the feilds !! ")

#TO REMOVE SELECTED ITEM
# def remove_record():
#     for i in tree.selection():
#         tree.delete(i)

textData = {
    'town' : 'Wałbrzych',
    'address_1' : 'ul. Truskawiecka 14/4',
    'address_2' : '58-301 Wałbrzych',
    'nip' : '886-301-82-63',
    'regon' : '520101773',
    'email' : 'g.ciesla@hantech.net.pl',
    'phone_number' : '+48 796 996 912',
    'bank_name' : 'Pekao S.A.',
    'account_number' : '37 1240 1952 1111 0011 3033 5600',
    'offer_number' : ''
    }

#CREATING THE GUI
locale.setlocale(locale.LC_ALL, 'pl_PL.UTF-8')
window = Tk()
window.geometry("1600x1200")
bg = PhotoImage(file='background_offer_1.png')
label_BG = Label(window, image=bg)
label_BG.place(x=0, y=0)
 



## GÓRNA SEKCJA

# label11=Label(window,text="Miejscowość",font="times 12")
# label11.place(x=500,y=100)
town = Entry(window, width=10)
town.place(x=640,y=90)
town.insert(0, "Wałbrzych")

date_entry = DateEntry(window, width=15, date_pattern="dd MM yyyy", borderwidth=2)
date_entry.place(x=740, y=90)
# date_entry.insert(0, datetime.datetime.now().strftime("%d %B %Y"))


address1_value = StringVar(window, value=textData['address_1'])
address1_entry=Entry(window, width=17, textvariable=address1_value)
address1_entry.place(x=110,y=118)

address2_value = StringVar(window, value=textData['address_2'])
address2_entry=Entry(window, width=17, textvariable=address2_value)
address2_entry.place(x=110,y=148)

nip_value = StringVar(window, value=textData['nip'])
nip_entry=Entry(window, width=15, textvariable=nip_value)
nip_entry.place(x=300,y=118)

regon_value = StringVar(window, value=textData['regon'])
regon_entry=Entry(window, width=15, textvariable=regon_value)
regon_entry.place(x=320,y=148)

email_value = StringVar(window, value=textData['email'])
email_entry=Entry(window, width=20, textvariable=email_value)
email_entry.place(x=485,y=118)

phone_value = StringVar(window, value=textData['phone_number'])
phone_entry=Entry(window, width=15, textvariable=phone_value)
phone_entry.place(x=485,y=148)

bank_name_value = StringVar(window, value=textData['bank_name'])
bank_name_entry=Entry(window, width=15, textvariable=bank_name_value)
bank_name_entry.place(x=715,y=118)

account_number_value = StringVar(window, value=textData['account_number'])
account_number_entry = Entry(window, width=25, textvariable=account_number_value)
account_number_entry.place(x=675,y=148)

## OFERTA / DOSTAWCA / KLIENT SEKCJA
offer_number_value = StringVar(window, value=textData['offer_number'])
offer_number_entry = Entry(window, width=25, textvariable=offer_number_value)
offer_number_entry.place(x=380,y=203)

supplier_name_entry = Entry(window, width=25)
supplier_name_entry.place(x=60,y=270)

supplier_address_1_entry = Entry(window, width=25)
supplier_address_1_entry.place(x=60,y=300)

supplier_address_2_entry = Entry(window, width=25)
supplier_address_2_entry.place(x=60,y=330)

supplier_nip_entry = Entry(window, width=25)
supplier_nip_entry.place(x=60,y=360)

client_name_entry = Entry(window, width=25)
client_name_entry.place(x=660,y=270)

client_address_1_entry = Entry(window, width=25)
client_address_1_entry.place(x=660,y=300)

client_address_2_entry = Entry(window, width=25)
client_address_2_entry.place(x=660,y=330)

client_nip_entry = Entry(window, width=25)
client_nip_entry.place(x=660,y=360)

# Client search button
search_client_button = Button(window, text="Szukaj klienta", command=lambda: open_client_search())
search_client_button.place(x=880, y=270)


 

#CREATING TABLE
columns = ('PID', 'PNAME', 'QTY','U_PRICE','TOTAL')

# table = Table.Table(window)

# tree = ttk.Treeview(window, columns=columns)
# tree.place(x=1000, y=1000)

# tree.column('PID', minwidth=0, width=20, stretch=NO)
# tree.column('PNAME', width=10)
# tree.column('QTY', width=10)
# tree.column('U_PRICE', width=10)
# tree.column('TOTAL', width=10)


# tree.heading('PID', text='Lp')
# tree.heading('PNAME', text='ProductName')
# tree.heading('QTY', text='Quantity')
# tree.heading('U_PRICE', text='UNIT PRICE')
# tree.heading('TOTAL', text='TOTAL')

# #INSERTING DATA INTO THE TABLE
# global count
# count=0
# data  = []
# for record in data:      
#     tree.insert(parent='',index='end'
#                ,iid = count,text='',values=record)      
#     count += 1
    
# tree.pack(side = BOTTOM,expand = True , fill = X)

##INSERT FEATURES
Input_frame = Frame(window)
Input_frame.place(x=875,y=825)

id = Label(Input_frame,text="ProductID")
id.grid(row=0,column=0)

ProductName= Label(Input_frame,text="ProductName")
ProductName.grid(row=0,column=1)

QNTY = Label(Input_frame,text="Quantity")
QNTY.grid(row=0,column=2)

UP = Label(Input_frame,text="UNIT PRICE")
UP.grid(row=0,column=3)

id_entry = Entry(Input_frame)
id_entry.grid(row=1,column=0)

ProductName_entry = Entry(Input_frame)
ProductName_entry.grid(row=1,column=1)

QNTY_entry = Entry(Input_frame)
QNTY_entry.grid(row=1,column=2)

UP_entry = Entry(Input_frame)
UP_entry.grid(row=1,column=3)

subtotallable = Label(window,text='SUBTOTAL :>>>',font="times 14")
subtotallable.place(x=1000,y=915)

subtotal = Entry(window,width = 10,font = ('Arial',16))
subtotal.place(x=1150,y=915)

taxlable=Label(window,text='18% GST:>>>',font="times 14")
taxlable.place(x=1000,y=950)

tax=Entry(window,width = 10,font = ('Arial',16))
tax.place(x=1150,y=950)

totallable=Label(window,text='TOTAL:>>>',font="times 14")
totallable.place(x=1000,y=985)

grandtotal = Entry(window,width = 10,font = ('Arial',16))
grandtotal.place(x=1150,y=985)

def get_clients_from_db():
    """Fetch all clients from the database"""
    try:
        conn = sqlite3.connect('DocumentsCreationData.db')
        cursor = conn.cursor()
        cursor.execute("SELECT Nip, CompanyName, AddressP1, AddressP2, Alias FROM Clients ORDER BY CompanyName")
        clients = cursor.fetchall()
        conn.close()
        return clients
    except sqlite3.Error as e:
        tkinter.messagebox.showerror("Database Error", f"Error accessing database: {e}")
        return []

def fill_client_data(client_data):
    """Fill client entry fields with selected client data"""
    nip, company_name, address1, address2, alias = client_data
    
    # Clear existing data
    client_name_entry.delete(0, END)
    client_address_1_entry.delete(0, END)
    client_address_2_entry.delete(0, END)
    client_nip_entry.delete(0, END)
    
    # Fill with selected client data
    client_name_entry.insert(0, company_name)
    client_address_1_entry.insert(0, address1)
    client_address_2_entry.insert(0, address2)
    client_nip_entry.insert(0, str(nip))

def on_client_select(event, search_window, client_listbox, clients):
    """Handle client selection from the listbox"""
    selection = client_listbox.curselection()
    if selection:
        selected_client = clients[selection[0]]
        fill_client_data(selected_client)
        search_window.destroy()

def open_client_search():
    """Open client search window"""
    clients = get_clients_from_db()
    if not clients:
        tkinter.messagebox.showinfo("No Clients", "No clients found in database.")
        return
    
    # Create search window
    search_window = Toplevel(window)
    search_window.title("Wybierz klienta")
    search_window.geometry("600x400")
    search_window.grab_set()  # Make window modal
    
    # Search label
    Label(search_window, text="Wybierz klienta z listy:", font=("Arial", 12)).pack(pady=10)
    
    # Create listbox with scrollbar
    frame = Frame(search_window)
    frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
    
    scrollbar = Scrollbar(frame)
    scrollbar.pack(side=RIGHT, fill=Y)
    
    client_listbox = Listbox(frame, yscrollcommand=scrollbar.set, font=("Arial", 10))
    client_listbox.pack(side=LEFT, fill=BOTH, expand=True)
    scrollbar.config(command=client_listbox.yview)
    
    # Populate listbox with client data
    for client in clients:
        nip, company_name, address1, address2, alias = client
        display_text = f"{alias} - {company_name} (NIP: {nip})"
        client_listbox.insert(END, display_text)
    
    # Bind double-click to select client
    client_listbox.bind('<Double-1>', lambda event: on_client_select(event, search_window, client_listbox, clients))
    
    # Add select button
    button_frame = Frame(search_window)
    button_frame.pack(pady=10)
    
    select_button = Button(button_frame, text="Wybierz", 
                          command=lambda: on_client_select(None, search_window, client_listbox, clients))
    select_button.pack(side=LEFT, padx=5)
    
    cancel_button = Button(button_frame, text="Anuluj", command=search_window.destroy)
    cancel_button.pack(side=LEFT, padx=5)

def ConvertDate(date : datetime.datetime) -> str:
    return date.strftime("%d %B %Y")

def GenerateOffer():
    doc = DocxTemplate('templates/offer_template.docx')
    context = {
        'town': town.get(),
        'address_1': address1_entry.get(),
        'address_2': address2_entry.get(),
        'nip': nip_entry.get(),
        'regon': regon_entry.get(),
        'email': email_entry.get(),
        'phone_number': phone_entry.get(),
        'bank_name': bank_name_entry.get(),
        'account_number': account_number_entry.get(),
        'offer_number': offer_number_entry.get(),
        'date': ConvertDate(date_entry.get_date()),
        'supplier_name': supplier_name_entry.get(),
        'supplier_address_1': supplier_address_1_entry.get(),
        'supplier_address_2': supplier_address_2_entry.get(),
        'supplier_nip': supplier_nip_entry.get(),
        'client_name': client_name_entry.get(),
        'client_address_1': client_address_1_entry.get(),
        'client_address_2': client_address_2_entry.get(),
        'client_nip': client_nip_entry.get()
    }

    doc.render(context)
    output_path = os.path.join('generated_docs', 'last_generated_offer.docx')
    doc.save(output_path)
    tkinter.messagebox.showinfo("Success", "Offer generated successfully!")


#BUTTONS
Insert_Button = Button(Input_frame,text = "INSERT PRODUCT")
Insert_Button.grid(row = 2, column = 2)
Remove_Button = Button(Input_frame,text = "REMOVE PRODUCT")
Remove_Button.grid(row = 2, column = 1)
Total_Button = Button(Input_frame,text = "TOTAL",command= Calc)
Total_Button.grid(row = 2, column = 0)
Save_Button = Button(Input_frame,text = "SAVE")
Save_Button.grid(row = 2, column = 3)
Generate_Offer_Button = Button(window, text="Twórz ofertę", command = GenerateOffer)
Generate_Offer_Button.place(x=700, y=800)


#db.close()
window.mainloop()