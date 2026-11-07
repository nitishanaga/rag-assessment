import os
import json
import argparse
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))

MEMORY_FILE = "memory.json"
LOG_FILE = "run_log.txt"
FINAL_OUTPUT_FILE = "final_lesson.txt"
MODEL_NAME = "openai/gpt-oss-20b"

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump({"past_mistakes_to_avoid": []}, f)
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def update_memory(distilled_lesson):
    if "System error" in distilled_lesson or "Unknown failure" in distilled_lesson or distilled_lesson == "None":
        return
    memory = load_memory()
    if distilled_lesson not in memory["past_mistakes_to_avoid"]:
        memory["past_mistakes_to_avoid"].append(distilled_lesson)
        memory["past_mistakes_to_avoid"] = memory["past_mistakes_to_avoid"][-5:]
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(memory, f, indent=4)

def fix_prompt(failed_prompt, evaluator_feedback):
    print("\n[PROMPT OPTIMIZER]: Analyzing memory.json and run_log.txt to rewrite the prompt...")
    memory = load_memory()
    past_mistakes = "\n- ".join(memory["past_mistakes_to_avoid"]) if memory["past_mistakes_to_avoid"] else "None."
    
    optimizer_instructions = f"""
    You are an expert Prompt Engineer. The AI Generator failed its evaluation.
    
    FAILED PROMPT USED:
    {failed_prompt}
    
    EVALUATOR JSON FEEDBACK (What went wrong):
    {evaluator_feedback}
    
    LONG-TERM MEMORY (Avoid these past mistakes):
    {past_mistakes}
    
    TASK: Write a brand-new, highly optimized prompt for the Generator. 
    - Explicitly command the Generator to fix the issues mentioned in the JSON feedback.
    - Ensure it explicitly teaches the 4 steps of RAG in order: (1) Indexing/Encoding (explain this as splitting documents into smaller parts and converting them into a searchable form), (2) Retrieval, (3) Augmentation (adding retrieved info to the prompt), (4) Generation.
    - DO NOT use the phrase 'summary fingerprint'.
    - Ensure it uses a simple, safe example (like a school library or college admissions). If it uses specific numbers or cutoff scores, it MUST explicitly label them as fictional or made-up sample values.
    - Output ONLY the new prompt text. No conversational filler.
    """
    
    response = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": optimizer_instructions}],
        model=MODEL_NAME, 
    )
    return response.choices[0].message.content.strip()

def generate_lesson(active_prompt):
    print("[GENERATOR]: Writing the lesson... Please wait.")
    response = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": active_prompt}],
        model=MODEL_NAME, 
    )
    return response.choices[0].message.content.strip()

def grade_lesson(lesson_text):
    print("[EVALUATOR]: Grading the lesson against strict JSON rubric...")
    rubric_prompt = f"""
    You are a strict Evaluator grading a beginner's lesson on RAG.
    
    LESSON TEXT:
    {lesson_text}
    
    Evaluate based on these 6 dimensions. You must return your response PURELY as a valid JSON object.
    
    JSON SCHEMA:
    {{
        "accurate": true/false, (Is it technically correct? MUST clarify that document indexing/encoding happens BEFORE retrieval. MUST explicitly state that retrieved information is added to the prompt (augmentation) BEFORE generation. RAG is NOT perfectly reliable.)
        "beginner_friendly": true/false, (Is it easy for a 12th grader in India to read? MUST NOT use the phrase 'summary fingerprint'.)
        "has_example": true/false, (Does it use a relatable real-world example? It MUST NOT use historical events or Siri/Alexa. ANY numbers or scores MUST be explicitly labeled as fictional/made-up.)
        "no_jargon": true/false, (Is it free of unexplained technical terms?)
        "covers_key_points": true/false, (Does it clearly explain WHAT it is, WHY it matters, and HOW it works?)
        "good_flow": true/false, (Does it have a clear introduction, middle, and conclusion?)
        "feedback_summary": "If any boolean is false, explain exactly what failed in one sentence. If all true, write 'Perfect'.",
        "distilled_lesson": "If any boolean is false, write a short, imperative rule for the AI to follow next time. If true, write 'None'."
    }}
    """
    
    response = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": rubric_prompt}],
        model=MODEL_NAME,
        response_format={"type": "json_object"} 
    )
    
    try:
        return json.loads(response.choices[0].message.content)
    except Exception:
        return {"accurate": False, "beginner_friendly": False, "has_example": False, "no_jargon": False, "covers_key_points": False, "good_flow": False, "feedback_summary": "System error.", "distilled_lesson": "None"}

def run_agent_loop(topic, is_demo=False):
    max_retries = 2
    
    if os.path.exists(FINAL_OUTPUT_FILE):
        os.remove(FINAL_OUTPUT_FILE)
        
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"--- RUN INITIATED FOR TOPIC: {topic} ---\n")
        f.write(f"Mode: {'DEMO (Intentional Failure)' if is_demo else 'NORMAL'}\n\n")
        
    memory = load_memory()
    past_mistakes = "\n- ".join(memory["past_mistakes_to_avoid"]) if memory["past_mistakes_to_avoid"] else "None yet."
    
    if is_demo:
        print("\n⚠️ RUNNING IN DEMO MODE: Forcing a bad prompt...")
        current_prompt = f"""
        Write a highly advanced, university-level academic paper about {topic}.
        DO NOT use any real-world examples. Use extreme technical jargon.
        Make sure to claim RAG is 100% flawless and ignore the augmentation step.
        Past mistakes to avoid: {past_mistakes}
        """
    else:
        print("\n✅ RUNNING IN NORMAL MODE: Attempting to write a perfect lesson...")
        current_prompt = f"""
        You are an AI teacher. Write a short lesson about {topic}.
        - The reader is a 12th-grade student from India. Use very simple English.
        - Explain how it works using these 4 steps in order: (1) Indexing/Encoding (explain this as splitting documents into smaller parts and converting them into a searchable form), (2) Retrieval of relevant info, (3) Augmentation (adding that info into the AI's prompt), (4) Generation of the final answer.
        - CRITICAL: Do NOT use the phrase 'summary fingerprint'.
        - Note: Do not claim RAG is 100% reliable (it only reduces hallucinations).
        - Use a simple real-world example like a college admissions system. If you use specific numbers or cutoff scores, you MUST explicitly label them as fictional or made-up sample values. 
        - CRITICAL: DO NOT use historical events, and DO NOT mention voice assistants like Siri or Alexa.
        Past mistakes to avoid: {past_mistakes}
        """
    
    for attempt in range(max_retries + 1):
        print(f"\n========== ATTEMPT {attempt + 1} ==========")
        
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"--- ATTEMPT {attempt + 1} PROMPT ---\n{current_prompt}\n\n")

        lesson = generate_lesson(current_prompt)
        grade_json = grade_lesson(lesson)
        print(f"[EVALUATOR RESULT]:\n{json.dumps(grade_json, indent=2)}")
        
        passed_all = (
            grade_json.get("accurate") is True and
            grade_json.get("beginner_friendly") is True and
            grade_json.get("has_example") is True and
            grade_json.get("no_jargon") is True and
            grade_json.get("covers_key_points") is True and
            grade_json.get("good_flow") is True
        )
        
        if passed_all:
            print("\n✅ SUCCESS! The lesson passed all 6 strict JSON checkpoints.")
            with open(FINAL_OUTPUT_FILE, "w", encoding="utf-8") as f:
                f.write(lesson)
                
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"Evaluator JSON (PASS):\n{json.dumps(grade_json, indent=2)}\n\n")
                f.write(f"Attempt {attempt + 1}: SUCCESS! Lesson passed all rubric checks and was saved to {FINAL_OUTPUT_FILE}.\n")
            break
            
        else:
            feedback = grade_json.get("feedback_summary", "Unknown failure.")
            distilled_lesson = grade_json.get("distilled_lesson", feedback)
            print(f"\n❌ FAILED: {feedback}")
            update_memory(distilled_lesson)
            
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"--- Attempt {attempt + 1} Failed ---\n")
                f.write(f"Evaluator JSON: {json.dumps(grade_json, indent=2)}\n")
                f.write(f"Action: Forwarding to Prompt Optimizer...\n\n")
            
            if attempt < max_retries:
                current_prompt = fix_prompt(current_prompt, json.dumps(grade_json))
                print("\n--- BRAND NEW PROMPT GENERATED BY THE OPTIMIZER ---")
                print(current_prompt)
            else:
                print("\n🚨 Maximum retries reached. The system stopped.")
                with open(LOG_FILE, "a", encoding="utf-8") as f:
                    f.write("SYSTEM HALTED: Maximum retries reached without passing evaluation.\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the AI Agentic Lesson Pipeline.")
    parser.add_argument("--demo", action="store_true", help="Start with a bad prompt to demonstrate the self-healing loop.")
    args = parser.parse_args()
    run_agent_loop("RAG (Retrieval-Augmented Generation)", is_demo=args.demo)