import os, zipfile, tempfile, dicom2nifti, glob, argparse

def main():
    p = argparse.ArgumentParser()
    p.add_argument("-i", help="Directory with zip files containing DICOM studies")
    p.add_argument("-o", help="Directory to store converted .nii.gz files")
    args = p.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    for idx, z in enumerate(sorted(glob.glob(f"{args.input_dir}/*.zip"))):
        base = os.path.splitext(os.path.basename(z))[0]
        name = f"{base}-{idx:04d}_0000.nii.gz"
        out = os.path.join(args.output_dir, name)
        with tempfile.TemporaryDirectory() as tmp:
            with zipfile.ZipFile(z) as zf:
                zf.extractall(tmp)
            dicom2nifti.dicom_series_to_nifti(tmp, out, reorient_nifti=True)

if __name__ == "__main__":
    main()
