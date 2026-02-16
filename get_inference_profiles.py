#!/usr/bin/env python3
"""
Helper script to list available Bedrock inference profiles
"""

import boto3
import json

def list_inference_profiles(region='us-west-2'):
    """List all available inference profiles in Bedrock."""
    try:
        bedrock = boto3.client('bedrock', region_name=region)
        
        print(f"Fetching inference profiles from {region}...\n")
        
        response = bedrock.list_inference_profiles()
        
        if not response.get('inferenceProfileSummaries'):
            print("No inference profiles found.")
            print("\nTrying to list foundation models instead...")
            
            # Try listing foundation models
            models_response = bedrock.list_foundation_models()
            
            print("\nAvailable Claude models:")
            for model in models_response.get('modelSummaries', []):
                if 'claude' in model['modelId'].lower():
                    print(f"\nModel ID: {model['modelId']}")
                    print(f"  Name: {model['modelName']}")
                    print(f"  Provider: {model.get('providerName', 'N/A')}")
                    print(f"  Input Modalities: {model.get('inputModalities', [])}")
                    print(f"  Output Modalities: {model.get('outputModalities', [])}")
            
            return
        
        print("Available Inference Profiles:\n")
        
        for profile in response['inferenceProfileSummaries']:
            print(f"Profile ARN: {profile['inferenceProfileArn']}")
            print(f"  Name: {profile['inferenceProfileName']}")
            print(f"  Type: {profile['type']}")
            print(f"  Status: {profile['status']}")
            if 'models' in profile:
                print(f"  Models: {profile['models']}")
            print()
        
        # Find Claude profiles
        claude_profiles = [p for p in response['inferenceProfileSummaries'] 
                          if 'claude' in p['inferenceProfileName'].lower()]
        
        if claude_profiles:
            print("\n" + "="*60)
            print("RECOMMENDED: Use one of these Claude profiles:")
            print("="*60)
            for profile in claude_profiles:
                print(f"\n{profile['inferenceProfileName']}:")
                print(f"  ARN: {profile['inferenceProfileArn']}")
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nTrying alternative approach...")
        
        # Try using cross-region inference profile IDs
        print("\nYou can try these cross-region inference profile IDs:")
        print("  - us.anthropic.claude-3-5-sonnet-20241022-v2:0")
        print("  - us.anthropic.claude-3-5-sonnet-20240620-v1:0")
        print("  - us.anthropic.claude-3-opus-20240229-v1:0")

if __name__ == "__main__":
    import sys
    
    region = sys.argv[1] if len(sys.argv) > 1 else 'us-west-2'
    
    print("Bedrock Inference Profile Finder")
    print("="*60)
    print(f"Region: {region}\n")
    
    list_inference_profiles(region)
    
    print("\n" + "="*60)
    print("To use a profile, update redshift_agent.py:")
    print("  model_id='<profile-arn-or-id-from-above>'")
    print("="*60)
