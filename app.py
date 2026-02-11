# -*- coding: utf-8 -*-

import streamlit as st
import requests
import json

import websocket
import threading
import queue

import pandas as pd
from streamlit.runtime.scriptrunner import add_script_run_ctx
import time


st.markdown('# CGRP Prototype')




def get_user(username, password):
    if not username:
        st.warning("Please enter an username.")
        return
    url = f"http://localhost:8000/user-find?username={username}"
    
    try:

        response = requests.get(url)
        

        if response.status_code == 200:
            item_data = response.json()
            user_obj = item_data[0]
            pass_in = user_obj['password']
            
            if(pass_in == password):
                return item_data
            else:
                st.error("Incorrect password")
                
        elif response.status_code == 404:
            st.error("User not found.")
        else:
            st.error(f"Error: {response.status_code} - {response.text}")
            
    except requests.exceptions.RequestException as e:
        st.error(f"Network error or API is down: {e}")

def initial_fields():
    if "device_status" not in st.session_state:
        st.session_state["device_status"] = False

    if "user_id" not in st.session_state:
        st.session_state["user_id"] = 0

    if "username" not in st.session_state:
        st.session_state["username"] = ""


    if "first_name" not in st.session_state:
        st.session_state["first_name"] = ""

    if "last_name" not in st.session_state:
        st.session_state["last_name"] = ""
    
    if "password" not in st.session_state:
            st.session_state["password"] = ""
        


@st.dialog("Sign In")
def show_dialog():
    initial_fields()
    st.write("Please enter your username and password")
    user = st.text_input("Username:")
    password = st.text_input("Password: ")
    
    if st.button("Enter"):
        user_data = get_user(user, password)
    
        if user_data:
            user_obj = user_data[0]
    
            st.session_state["user_id"] = user_obj["user_id"]
            st.session_state["username"] = user_obj["username"]
            st.session_state["first_name"] = user_obj["first_name"]
            st.session_state["last_name"] = user_obj["last_name"]
    
            st.session_state["device_status"] = True
            st.session_state["setup"] = True
            st.rerun()

if "setup" not in st.session_state:
        st.session_state["setup"] = False

if st.button("Log In"):
    show_dialog()
    
 
if st.session_state["setup"]:               
    userid = st.session_state["user_id"]
    uri = f"ws://localhost:8000/ws/device-data?user_id={userid}"


    if "message_queue" not in st.session_state:
        print("queue initialized")
        st.session_state.message_queue = queue.Queue(maxsize=1000)
    if "websocket_thread" not in st.session_state:
        st.session_state.websocket_thread = None
    if "data_container" not in st.session_state:
        st.session_state.data_container = pd.DataFrame(columns = ["user_id", "timestamp", "value"])
    if "device_connections" not in st.session_state:
        st.session_state.device_connections = ""
        
    
    
    def on_message(ws, message):
        print("connected")
        st.session_state.device_connections = "Connection Active: Recieving Data" 
        st.session_state.message_queue.put(message)
    
    def on_error(ws, error):
        print(f"WebSocket error: {error}")
        st.session_state.device_connections = "Connection Error" 
    
    def on_close(ws, close_status_code, close_msg):
        st.session_state.device_connections = "Connection Inactive" 
        print("WebSocket closed")
    
    def on_open(ws):
        st.session_state.device_connections = "Connection Active" 
        print("WebSocket connection opened")
        
        
    
    def run_websocket_client(websocket_url):
        ws = websocket.WebSocketApp(websocket_url,
                                    on_open=on_open,
                                    on_message=on_message,
                                    on_error=on_error,
                                    on_close=on_close)
        
        add_script_run_ctx(threading.current_thread()) 
        ws.run_forever()
    
    @st.fragment(run_every="1s")
    def create_feed(chart, num):
        #expander.empty()
        #expander.write(st.session_state.device_connections)
        if "message_queue" not in st.session_state:
            #st.session_state.device_connections = "Connection Active"
            return
    
        while not st.session_state.message_queue.empty():
            message = st.session_state.message_queue.get()
            
            
            try:
                data = json.loads(message)
                
                new_row = pd.DataFrame([data], columns = ["user_id", "timestamp", "value"])
                new_row["timestamp"] = pd.to_datetime(new_row["timestamp"], format='ISO8601')
                new_row["time"] = new_row["timestamp"].dt.strftime("%I:%M:%S %p")
                curr_val = round(new_row.iat[0,2])
                curr_val = str(curr_val)
                
                st.session_state.data_container = pd.concat([st.session_state.data_container, new_row], ignore_index = True)
            except json.JSONDecodeError:
                st.warning("non-JSON message")
                
            if st.session_state.data_container.shape[0] <= 2:
                num.markdown(f"# {curr_val} ")
            else:
                y_slope = st.session_state.data_container.iloc[-1, 2] - st.session_state.data_container.iloc[-2, 2]
                x_slope = st.session_state.data_container.iloc[-1, 1] - st.session_state.data_container.iloc[-2, 1]
                x_slope = x_slope.total_seconds()
                slope = y_slope/x_slope 
                if(slope > 0):
                    num.title(f":green[{curr_val} ]" + ":green[^]")
                elif(slope < 0):
                    num.title(f":red[{curr_val}] " + ":red[v]")
                else:
                    num.title(f"{curr_val} " + "-")
                    
            if st.session_state.data_container.shape[0] <= 50:
                chart.line_chart(st.session_state.data_container, x = "time", y = "value", x_label = "", y_label = "CGRP Level")
                #placeholder.dataframe(st.session_state.data_container)
            else:
                chart.line_chart(st.session_state.data_container.iloc[-50:-1] , x = "time", y = "value", x_label = "", y_label = "CGRP Level")
                #placeholder.dataframe(st.session_state.data_container.iloc[-50:-1])
            
            
            
            
            
            
    
        
    
    start_processing = st.button("Sync with Device")
    
    st.write(f"Welcome {st.session_state["first_name"]} {st.session_state["last_name"]}")
    
    name = st.session_state["username"]

    
    load_start = False
    if start_processing and st.session_state.websocket_thread is None:
        success_message1 = st.success("Connecting to your device...")
        st.session_state.websocket_thread = threading.Thread(
            target=run_websocket_client, 
            args=(uri,), 
            daemon=True
        )
        add_script_run_ctx(st.session_state.websocket_thread)
        st.session_state.websocket_thread.start()
        
        time.sleep(2)
        success_message1.empty()
        success_message = st.success("Connection successful")
        time.sleep(2)
        success_message.empty()
        load_start = True
    
    if load_start:
        st.markdown(f"# {name}'s Dashboard")
        curr_val = st.empty()
        
        placeholder_df = pd.DataFrame(columns = ["user_id", "timestamp", "value", "disp_time"])
        placeholder_df["timestamp"] = pd.to_datetime(placeholder_df["timestamp"], format='ISO8601').dt.time
        live_chart = st.line_chart(placeholder_df, x = "timestamp", y = "value")
    
        #placeholder = st.empty()
        
        #expander = st.expander("See device status")
        #expander.write("")
        
        create_feed(live_chart, curr_val)





