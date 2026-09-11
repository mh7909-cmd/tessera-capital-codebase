import json, os

def clear_dal_history():
    state_path = 'Email/workspace/skills/outreach/campaign_state.json'
    if not os.path.exists(state_path):
        return
        
    with open(state_path, 'r') as f:
        state = json.load(f)
        
    threads = state.get('threads', {})
    keys_to_clean = []
    
    for k, v in threads.items():
        if v.get('ticker') == 'DAL':
            # Reset history to only have the assistant outreach
            if len(v['history']) > 1:
                v['history'] = v['history'][:1]
                v['status'] = 'waiting'
    
    with open(state_path, 'w') as f:
        json.dump(state, f, indent=4)
        
    print("Cleared history for DAL threads.")

if __name__ == "__main__":
    clear_dal_history()
