import urllib.request
import json

def main():
    try:
        url = "http://127.0.0.1:8000/stocks/7203/tab/chart"
        html = urllib.request.urlopen(url).read().decode('utf-8')
        
        # Payload JSONを抽出
        start_marker = 'id="chart-payload-json"'
        start_idx = html.find(start_marker)
        if start_idx == -1:
            print("Could not find chart-payload-json script tag")
            return
            
        start = html.find('>', start_idx) + 1
        end = html.find('</script>', start)
        payload_str = html[start:end].strip()
        payload = json.loads(payload_str)
        
        points = payload.get('points', [])
        print(f"Total points: {len(points)}")
        if points:
            last_point = points[-1]
            print("Last point keys:", list(last_point.keys()))
            print("Last 3 points details:")
            for p in points[-3:]:
                print(f"  Date: {p.get('label')}, Open: {p.get('open')}, High: {p.get('high')}, Low: {p.get('low')}, Close: {p.get('close')}, SMA25: {p.get('SMA25')}")
            
            # GC/DCの発生を確認（短期SMA25と長期SMA75）
            crosses = []
            k1 = "SMA25"
            k2 = "SMA75"
            for i in range(1, len(points)):
                prev1 = points[i-1].get(k1)
                prev2 = points[i-1].get(k2)
                curr1 = points[i].get(k1)
                curr2 = points[i].get(k2)
                if prev1 is not None and prev2 is not None and curr1 is not None and curr2 is not None:
                    if prev1 < prev2 and curr1 >= curr2:
                        crosses.append((i, "Golden", points[i]['label']))
                    elif prev1 > prev2 and curr1 <= curr2:
                        crosses.append((i, "Dead", points[i]['label']))
            print(f"Cross events in whole dataset (total {len(crosses)}):")
            for idx, ctype, date in crosses:
                # 直近100件に入っているかも確認
                in_view = idx >= (len(points) - 100)
                print(f"  Index: {idx}, Type: {ctype}, Date: {date}, In recent 100: {in_view}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()
