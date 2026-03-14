#!/bin/bash
# Create DynamoDB tables for VTA
# Usage: bash create_tables.sh [region]

set -euo pipefail

REGION="${1:-us-east-1}"

echo "===== Creating VTA DynamoDB Tables (region: $REGION) ====="

# Table 1: Curriculum
echo "[1/3] Creating vta_curriculum..."
aws dynamodb create-table \
  --table-name vta_curriculum \
  --attribute-definitions \
    AttributeName=tutorial_id,AttributeType=S \
    AttributeName=task_id,AttributeType=S \
  --key-schema \
    AttributeName=tutorial_id,KeyType=HASH \
    AttributeName=task_id,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --region "$REGION" \
  2>/dev/null && echo "  Created vta_curriculum" || echo "  vta_curriculum already exists"

# Table 2: Session State
echo "[2/3] Creating vta_session_state..."
aws dynamodb create-table \
  --table-name vta_session_state \
  --attribute-definitions \
    AttributeName=session_id,AttributeType=S \
    AttributeName=task_sort_key,AttributeType=S \
  --key-schema \
    AttributeName=session_id,KeyType=HASH \
    AttributeName=task_sort_key,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --region "$REGION" \
  2>/dev/null && echo "  Created vta_session_state" || echo "  vta_session_state already exists"

# Table 3: Sessions
echo "[3/3] Creating vta_sessions..."
aws dynamodb create-table \
  --table-name vta_sessions \
  --attribute-definitions \
    AttributeName=session_id,AttributeType=S \
  --key-schema \
    AttributeName=session_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region "$REGION" \
  2>/dev/null && echo "  Created vta_sessions" || echo "  vta_sessions already exists"

echo ""
echo "===== DynamoDB Tables Ready ====="
echo "Seed curriculum with: python3 -m vta.curriculum.seed_curriculum --file vta/curriculum/linux_basics.json"
