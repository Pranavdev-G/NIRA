import kagglehub

# Download latest version
print("Starting download of 'uttejkumarkandagatla/fall-detection-dataset'...")
path = kagglehub.dataset_download("uttejkumarkandagatla/fall-detection-dataset")

print("Path to dataset files:", path)
