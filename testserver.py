# coding=utf8
import requests
import json


url1 = 'http://127.0.0.1:8898/tranforImage'

url1 = 'http://127.0.0.1:8898/tranforImage'
#url2 = 'http://127.0.0.1:8898/genImage'
url2 = 'http://175.27.190.185:8898/genImage'
url2 = 'http://127.0.0.1:8898/genImage'


url3 = 'http://127.0.0.1:8898/mergeImage'

url4 = 'http://127.0.0.1:8891/mergeImageflow'
#url3 = 'http://43.133.208.206:8898/mergeImage'
data1={
"style":"https://seopic.699pic.com/photo/40094/7630.jpg_wh1200.jpg",
"content":"https://seopic.699pic.com/photo/50113/4678.jpg_wh1200.jpg"
}

data2={
"object":"an avocado",
"accessories":"in a christmas sweater",
"behavior":"playing chess"
}

data3={
        "01_background": "0_no_attributes",
        "02_shadow": "0_no_attributes",
        "03_feet": "0_no_attributes",
        "04_body": "body",
        "05_cloth": "victory",
        "06_shoe": "sandy",
        "07_item": "ice_cream",
        "08_hand": "0_no_attributes",
        "09_sleeve": "sandy",
        "10_face": "nah",
        "11_head": "vitory_hat",
        "12_glasses": "goofy_goober_glasses",
        "genImageName":"haha"
    }

datas= {
        "01_background": "0_no_attributes",
        "02_shadow": "0_no_attributes",
        "03_feet": "https://api.forart.ai/api/forart/minio/1479452956293099521_feet_1.png",
        "04_body": "https://api.forart.ai/api/forart/minio/1479452674318430209_body_1.png",
        "05_cloth": "https://api.forart.ai/api/forart/minio/1479452829612535810_cloth_61.png",
        "06_shoe": "https://api.forart.ai/api/forart/minio/1479453406325141505_shoe_1.png",
        "07_item": "https://api.forart.ai/api/forart/minio/1479453334095032322_item_92.png",
        "08_hand": "https://api.forart.ai/api/forart/minio/1479453189244743682_hand_1.png",
        "09_sleeve": "http://chuantu.xyz/t6/742/1641520355x2890305113.png",
        "10_face": "http://chuantu.xyz/t6/742/1641520355x2890305113.png",
        "11_head": "0_no_attributes",
        "12_glasses": "https://api.forart.ai/api/forart/minio/1479453048249020417_glasses_1.png",
        "genImageName":"haha"
    }


data4= {
        "04_body": "http://chuantu.xyz/t6/742/1645143040x2728309567.jpg",
        "05_cloth": "http://chuantu.xyz/t6/742/1645143040x2728309567.jpg",
        "genImageName":"haha"
    }


datas2=["https://api.forart.ai/api/forart/minio/1479452956293099521_feet_1.png",
        "https://api.forart.ai/api/forart/minio/1479452674318430209_body_1.png",
        "https://api.forart.ai/api/forart/minio/1479452829612535810_cloth_61.png" 
        ]

url6 = 'http://127.0.0.1:8892/tranforImage'
datas6={"content":"https://raw.githubusercontent.com/jcjohnson/neural-style/master/examples/inputs/golden_gate.jpg",
        "style":"https://raw.githubusercontent.com/jcjohnson/neural-style/master/examples/inputs/starry_night.jpg",
        "iteration":500,
        "imageSize":512,
        "threshold":0.015,
        }

res = requests.post(url=url6,data=json.dumps(datas6),verify=False)
print(res.text)
#print(res.json()["query_list"])
