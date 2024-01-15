import json
import os
import nltk
import time
import torch
from transformers import pipeline,AutoTokenizer,AutoModelForSeq2SeqLM
from waitress import serve
from flask import Flask, request, Response
from flask_cors import CORS, cross_origin
from utils import audio_extract, whisper_infer
from inference_detect import *
import menovideo.menovideo as menoformer
import detect_violence
import opennsfw2 as n2

app = Flask(__name__)

LANGUAGES = {
    "vietnamese": "vi",
    "chinese": "zh",
    "english": "en"
}

SUB_OUTPUT = "http://210.245.90.204:13000/hg_project_effect/movie_classify/subs"

@app.route("/api/speech2text", methods=["POST", "GET"])
def speech2text():
    video_path = request.args.get("video_path")

    # get language id
    language = LANGUAGES[request.args.get("language")]
    
    if video_path is not None:
        # get audio
        audio_path = audio_extract(video_path)
        
        srt_file_name = audio_path.split("/")[-1].replace("mp3", "srt")
        srt_file = os.path.join(SUB_OUTPUT, srt_file_name)
        
        # speech to text
        sub_path = whisper_infer(
            audio_path=audio_path,
            language=language,
            srt_file=srt_file_name
        )
        
        return {"sub_path": srt_file, "status": 200, "user_id": 1}
    else:
        message = "No video path"
        return Response((message), status=400)

@app.route("/api/detetcion_text", methods=["POST","GET"])
def summary():
    start_time=time.time()
    file_path="sub_path"
    with open(file_path,"r") as f:
        a=f.read().strip("\n")
    tokenizer=AutoTokenizer.from_pretrained("D:\Work\MODEL\summary-bart-large-cnn")
    sentences=nltk.tokenize.sent_tokenize(a)
    #Seperate the file if the file is too long compare to the model
    length=0
    chunk=""
    chunks=[]
    count=-1
    for sentence in sentences:
        count+=1
        combined_length=len(tokenizer.tokenize(sentence)) +length
        
        if combined_length <= tokenizer.max_len_single_sentence:
            chunk+=sentence + ""
            length=combined_length
            if count==len(sentences) -1:
                chunks.append(chunk.strip())
        else:
            chunks.append(chunk.strip())
            
            length=0
            chunk=""
            chunk+=sentence+ " "
            length=len(tokenizer.tokenize(sentence))

    inputs=[tokenizer(chunk,return_tensors="pt").to("cuda") for chunk in chunks]
    # model=AutoModelForSeq2SeqLM.from_pretrained("pszemraj/long-t5-tglobal-base-16384-book-summary")
    model=AutoModelForSeq2SeqLM.from_pretrained("D:\Work\MODEL\summary-bart-large-cnn").to("cuda")
    with open("summary.txt","w") as f:
        pass
    for input in inputs:
        outputs=model.generate(**input,max_length=512)
        with open("summary.txt","a") as f:
            f.write(tokenizer.decode(*outputs,skip_special_tokens=True))

    end_time = time.time()
    execution_time = end_time - start_time

    minutes, seconds = divmod(execution_time, 60)
    time_format = "{:02d}:{:02d}".format(int(minutes), int(seconds))

    del tokenizer, model

    print("Execution time:", time_format)

@app.route("/api/detetcion_text", methods=["POST","GET"]) 
def detection_text():
    subs=pysrt.open("sub_path")
    results = []
    for sub in subs:
        inputs=tokenizer(sub.text,padding=True,truncation=True,max_length=512,return_tensors="pt").to("cuda")
        outputs=model(**inputs)
        probs=outputs[0].softmax(1)
        pred_label_idx=probs.argmax()
        pred_label=model.config.id2label[pred_label_idx.item()]
        result = {
                'pred_label_idx': pred_label_idx.item(),
                'pred_label': pred_label,
                'text': sub.text,
                'start': {'minutes': sub.start.minutes, 'seconds': sub.start.seconds},
                'end': {'minutes': sub.end.minutes, 'seconds': sub.end.seconds}
            }
        results.append(result)
    with open('results.json', 'w') as f:
        json.dump(results, f) 
    return results

@app.route("/api/detetcion_violence", methods=["POST","GET"])
def detect_violence():
    model = menoformer.DeVTr()
    detect_violence.resume_checkpoint(model, '/home/www/data/data/saigonmusic/Dev_AI/kiendn/detect_violence/checkpoint/checkpoint-epoch10.pth')
    video_path = request.args.get("video_path")
    videos, intervals = detect_violence.capture(video_path,timesep=40,rgb=3,h=200,w=480,frame_interval=3)
    device =  'cuda' if torch.cuda.is_available() else 'cpu'
    model.to(device)
    predictions = []
    for index in range(len(intervals)):
        sample = torch.unsqueeze(videos[index],0).to(device)
        output = model(sample)
        predictions.append({
            "start":intervals[index][0], 
            "end":intervals[index][1],
            "prediction":torch.sigmoid(output)[0].item(), 
        })
    return json.dumps(predictions)

@app.route("/api/detetcion_pornography", methods=["POST","GET"])
def detect_pornography():
    video_path = request.args.get("video_path")
    elapsed_seconds, nsfw_probabilities = n2.predict_video_frames(video_path)
    sum_nsfw = 0
    count = 0
    start = 0
    end = 0
    predictions = []
    for i in range(len(nsfw_probabilities)):
        if nsfw_probabilities[i] >= 0.5:
            if count == 0:
                start = elapsed_seconds[i]
            count += 1
            sum_nsfw += nsfw_probabilities[i]
        else:
            if count !=0:
                end = elapsed_seconds[i-1]
                predictions.append({
                    'start':start,
                    'end':end,
                    'avg_nsfw_score': sum_nsfw/count
                })
                count = 0
                sum_nsfw = 0
    if count != 0:
        end = elapsed_seconds[i]
        predictions.append({
            'start':start,
            'end':end,
            'avg_nsfw_score': sum_nsfw/count
        })
    return json.dumps(predictions)
serve(app, host="0.0.0.0", port=6001, threads=15)