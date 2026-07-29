# py-dpvz Spack Repository

This custom Spack repository allows you to easily install the `py-dpvz` Python wrapper into your Spack environments.

## Target Workflows

### Workflow A: External MPI (Using ParaView's embedded MPI)
If you are using ParaView binaries that ship with their own embedded MPI, you can configure Spack to use that MPI as an external dependency to prevent ABI mismatches.

1. Run the `dpvtkmpiinfo.py` utility against your ParaView binary:
   ```bash
   python3 scripts/dpvtkmpiinfo.py /path/to/paraview/bin/pvbatch
   ```
2. Copy the generated `Spack External Package Snippet` output.
3. Paste the snippet into your `spack.yaml` environment file under the `packages:` section.
4. Add this custom repository to your Spack environment:
   ```bash
   spack repo add ./spack-repo
   ```
5. Install the package:
   ```bash
   spack install py-dpvz
   ```

### Workflow B: Existing ParaView Environment
If you are building inside an existing Spack environment where ParaView (and its MPI provider) was already built by Spack:

1. Add this custom repository to your Spack environment:
   ```bash
   spack repo add ./spack-repo
   ```
2. Install the package, allowing Spack to resolve dependencies automatically:
   ```bash
   spack install py-dpvz
   ```

## Local Development
By default, the `package.py` points to the remote GitHub repository. If you are developing locally and want Spack to build from your local cloned source code:

1. Open `spack-repo/packages/py-dpvz/package.py`.
2. Comment out the default `git = "https://..."` line.
3. Uncomment the local file URL line: 
   `git = f"file://{os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))}"`
4. Run `spack install py-dpvz`.
