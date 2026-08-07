from downloader import generate_earth
from processor import process_outputs

import os
import json
import traceback

from datetime import datetime, timedelta, timezone



# =========================
# History 配置
# =========================

HISTORY_DIR = "history"

HISTORY_JSON = "history.json"

KEEP_HOURS = 24





# =========================
# 清理24小时以前历史
# =========================

def cleanup_history():

    print("\n[3] Cleanup history")


    if not os.path.exists(HISTORY_JSON):

        print(
            "No history.json found"
        )

        return



    try:


        with open(
            HISTORY_JSON,
            "r",
            encoding="utf-8"
        ) as f:

            records = json.load(f)



    except Exception as e:


        print(
            "Read history failed:",
            e
        )

        return




    now = datetime.now(
        timezone.utc
    )


    cutoff = (
        now -
        timedelta(
            hours=KEEP_HOURS
        )
    )



    keep=[]



    for item in records:


        try:


            t = datetime.fromisoformat(
                item["time"]
                .replace(
                    "Z",
                    "+00:00"
                )
            )



            if t >= cutoff:


                keep.append(item)



            else:


                image = item.get(
                    "image"
                )



                if image and os.path.exists(image):


                    os.remove(image)


                    print(
                        "Removed:",
                        image
                    )



        except Exception as e:


            print(
                "Skip invalid record:",
                e
            )




    with open(
        HISTORY_JSON,
        "w",
        encoding="utf-8"
    ) as f:


        json.dump(
            keep,
            f,
            indent=2,
            ensure_ascii=False
        )



    print(
        "History kept:",
        len(keep),
        "frames"
    )






# =========================
# 主程序
# =========================

def main():

    print("="*40)

    print(
        "Himawari Earth Generator"
    )

    print("="*40)



    try:


        print("\n[1] Download")


        success = generate_earth()



        if not success:


            print(
                "\nNo satellite image available"
            )


            print(
                "Skip this update"
            )


            return




        print("\n[2] Process")


        process_outputs()



        cleanup_history()



        print(
            "\nDONE"
        )



    except Exception:


        print(
            "\nFAILED"
        )


        traceback.print_exc()


        # 不主动raise
        # 保证定时任务不中断






if __name__ == "__main__":

    main()
