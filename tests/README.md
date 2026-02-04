# LocalStack CLI Tests

This directory contains tests for LocalStack.

## Usage

By default, we filtered out commands that use ID parameters and file parameters.

```bash
python print_commands_with_endpoint.py --endpoint http://localhost:4566 > test.sh
```

Start LocalStack

```bash
localstack start
```

Run the evaluation script

```bash
python eval_ls.py test.sh

...
================================================================================
Command 249/260
================================================================================
Command: aws --endpoint-url=http://localhost:4566 ec2 register-image --name my-image --image-location amzn-s3...
  → Restarting LocalStack...
  → Waiting for LocalStack to be ready...
  → Running command...
  ✓ Success (exit code: 0)
  → Saving checkpoint...

================================================================================
Command 250/260
================================================================================
Command: aws --endpoint-url=http://localhost:4566 ec2 register-image --name my-image --root-device-name /dev/...
  → Restarting LocalStack...
  → Waiting for LocalStack to be ready...
  → Running command...
  ✓ Success (exit code: 0)
  → Saving checkpoint...
...
```

## Results

The results are saved in the `eval_results.json` file.

```bash
python analyze_results.py eval_results.json

================================================================================
EVALUATION COMPLETE
================================================================================
Total commands: 263
Successful: 121 (46.0%)
...
```