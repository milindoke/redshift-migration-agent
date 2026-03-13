#!/usr/bin/env python3
"""CDK app entry point for the Redshift Modernization Agents stack.

Requirements: 9.1
"""
import aws_cdk as cdk

from stack import RedshiftModernizationStack

app = cdk.App()
RedshiftModernizationStack(app, "RedshiftModernizationStack")
app.synth()
