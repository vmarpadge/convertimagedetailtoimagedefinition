import json
import boto3
import zipfile
import tempfile
import botocore
from boto3.session import Session


code_pipeline = boto3.client('codepipeline')

def lambda_handler(event, context):
    print(event)
    
    job_id = event['CodePipeline.job']['id']
    bucketN = event['CodePipeline.job']['data']['inputArtifacts'][0]['location']['s3Location']['bucketName']
    objectK = event['CodePipeline.job']['data']['inputArtifacts'][0]['location']['s3Location']['objectKey']
    
    conatiner_name = event['CodePipeline.job']['data']['actionConfiguration']['configuration']['UserParameters']
    
    key_id = event['CodePipeline.job']['data']['artifactCredentials']['accessKeyId']
    key_secret = event['CodePipeline.job']['data']['artifactCredentials']['secretAccessKey']
    session_token = event['CodePipeline.job']['data']['artifactCredentials']['sessionToken']
    
    print(conatiner_name)
    print(key_id)
    
    session = Session(aws_access_key_id=key_id, aws_secret_access_key=key_secret, aws_session_token=session_token)
    s3 = session.client('s3', config=botocore.client.Config(signature_version='s3v4'))
    
    outputN = event['CodePipeline.job']['data']['outputArtifacts'][0]['location']['s3Location']['bucketName']
    outputK = event['CodePipeline.job']['data']['outputArtifacts'][0]['location']['s3Location']['objectKey']

    try:   
        tmp_file = tempfile.NamedTemporaryFile()
        with tempfile.NamedTemporaryFile() as tmp_file:
            s3.download_file(bucketN, objectK, tmp_file.name)
            with zipfile.ZipFile(tmp_file.name, 'r') as zip:

                json_data = zip.read('imageDetail.json')
                obj = json.loads(json_data)
            
                image_uri = obj['ImageURI'].split('@')[0]
                image_tag = obj['ImageTags'][0]

                image = f"{image_uri}:{image_tag}"
                print(image)

                definition = [{
                    'name': conatiner_name,
                    'imageUri': image
                }]
                
                print(definition)

                with open('/tmp/imagedefinitions.json', 'w') as outfile:
                    json.dump(definition, outfile)
                
                with zipfile.ZipFile('/tmp/imagedefinitions.zip', mode='w') as zipf:
                    zipf.write('/tmp/imagedefinitions.json', arcname='imagedefinitions.json')
                    
                response = s3.upload_file('/tmp/imagedefinitions.zip', outputN, outputK, ExtraArgs={"ServerSideEncryption": "aws:kms"})
                code_pipeline.put_job_success_result(jobId=job_id)
                
    except Exception as error:
        response = code_pipeline.put_job_failure_result(
            jobId=job_id,
            failureDetails={
                'type': 'JobFailed',
                'message': f'{error.__class__.__name__}: {str(error)}'
            }
        )
    return response
