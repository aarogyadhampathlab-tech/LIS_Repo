import os
import datetime
from config import WATCH_FOLDER

def create_fake_log():
    # 1. Ensure the watch folder exists
    if not os.path.exists(WATCH_FOLDER):
        os.makedirs(WATCH_FOLDER)

    # 2. Create a filename like the real lab (MMDDYYYY_R.log)
    filename = datetime.datetime.now().strftime("%m%d%Y_test_R.log")
    file_path = os.path.join(WATCH_FOLDER, filename)

    # 3. Fake data using tabs (\t) as the lab does
    # Format: [Date] \t [Patient Name] \t [ID] \t [?] \t [Test ID] \t [Result]
    fake_data = (
        "2023-10-27\tJOHN DOE\t12345\t0\t768\t1.2 mg/dL\n"
        "2023-10-27\tJANE SMITH\t67890\t0\t301\t95 mg/dL\n"
    )

    with open(file_path, "w") as f:
        f.write(fake_data)
    
    print(f"✅ Success! Created {filename} in your watch folder.")

if __name__ == "__main__":
    create_fake_log()
