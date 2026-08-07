from downloader import generate_earth
from processor import process_outputs

import traceback



def main():

    print("="*40)
    print("Himawari Earth Generator")
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
