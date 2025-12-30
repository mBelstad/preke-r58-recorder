#!/bin/bash
# VPU Health Check Script for Rockchip RK3588
# Monitors Video Processing Unit resource usage to prevent crashes

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "======================================"
echo " RK3588 VPU Health Check"
echo "======================================"
echo ""

# Check if running on correct hardware
if [[ ! -f /proc/device-tree/model ]]; then
    echo -e "${RED}Error: Cannot detect device model${NC}"
    exit 1
fi

MODEL=$(cat /proc/device-tree/model 2>/dev/null || echo "Unknown")
echo "Device Model: $MODEL"
echo ""

# Function to check MPP service sessions
check_mpp_sessions() {
    echo "--- MPP Service Sessions ---"
    
    if [[ -f /sys/kernel/debug/mpp_service/session ]]; then
        session_count=$(cat /sys/kernel/debug/mpp_service/session | grep -c "session" || echo "0")
        
        echo "Active MPP Sessions: $session_count"
        
        if [[ $session_count -gt 8 ]]; then
            echo -e "${RED}⚠️  WARNING: High VPU session count! ($session_count > 8)${NC}"
            echo "This may cause system instability and crashes."
        elif [[ $session_count -gt 6 ]]; then
            echo -e "${YELLOW}⚠️  CAUTION: VPU usage is high ($session_count sessions)${NC}"
        else
            echo -e "${GREEN}✓ VPU session count is healthy${NC}"
        fi
        
        echo ""
        echo "Session details:"
        cat /sys/kernel/debug/mpp_service/session
        echo ""
    else
        echo -e "${YELLOW}MPP session info not available (requires root or debugfs)${NC}"
        echo ""
    fi
}

# Function to check running GStreamer processes
check_gstreamer_processes() {
    echo "--- GStreamer Processes ---"
    
    gst_count=$(ps aux | grep -E "gst-launch|python.*pipeline|python.*ingest|python.*recorder|python.*mixer" | grep -v grep | wc -l)
    
    echo "Active GStreamer-related processes: $gst_count"
    
    if [[ $gst_count -gt 6 ]]; then
        echo -e "${YELLOW}⚠️  Many GStreamer processes detected${NC}"
    else
        echo -e "${GREEN}✓ Process count is normal${NC}"
    fi
    
    echo ""
    echo "Process list:"
    ps aux | grep -E "gst-launch|python.*pipeline|python.*ingest|python.*recorder|python.*mixer" | grep -v grep | head -10
    echo ""
}

# Function to check for hardware encoder/decoder usage
check_encoder_decoder_usage() {
    echo "--- Hardware Encoder/Decoder Usage ---"
    
    # Count mpph264enc instances
    mpph264_count=$(ps aux | grep -o "mpph264enc" | wc -l)
    # Count mpph265enc instances  
    mpph265_count=$(ps aux | grep -o "mpph265enc" | wc -l)
    # Count mppvideodec instances
    mppvideodec_count=$(ps aux | grep -o "mppvideodec" | wc -l)
    
    total_mpp=$((mpph264_count + mpph265_count + mppvideodec_count))
    
    echo "Hardware Encoders (mpph264enc): $mpph264_count"
    echo "Hardware Encoders (mpph265enc): $mpph265_count"
    echo "Hardware Decoders (mppvideodec): $mppvideodec_count"
    echo "Total MPP elements: $total_mpp"
    
    if [[ $total_mpp -gt 8 ]]; then
        echo -e "${RED}⚠️  CRITICAL: Too many hardware encoder/decoder instances! ($total_mpp > 8)${NC}"
        echo "This WILL cause crashes. Stop some pipelines immediately."
    elif [[ $total_mpp -gt 6 ]]; then
        echo -e "${YELLOW}⚠️  WARNING: High hardware encoder/decoder usage ($total_mpp)${NC}"
    else
        echo -e "${GREEN}✓ Hardware encoder/decoder usage is healthy${NC}"
    fi
    echo ""
}

# Function to check memory usage
check_memory() {
    echo "--- Memory Usage ---"
    
    free -h
    echo ""
    
    # Check for memory pressure
    mem_available=$(free -m | awk 'NR==2 {print $7}')
    mem_total=$(free -m | awk 'NR==2 {print $2}')
    mem_percent=$((100 * mem_available / mem_total))
    
    if [[ $mem_percent -lt 20 ]]; then
        echo -e "${RED}⚠️  WARNING: Low memory available (${mem_percent}%)${NC}"
    elif [[ $mem_percent -lt 40 ]]; then
        echo -e "${YELLOW}⚠️  CAUTION: Memory usage is high (${mem_percent}% available)${NC}"
    else
        echo -e "${GREEN}✓ Memory usage is healthy (${mem_percent}% available)${NC}"
    fi
    echo ""
}

# Function to check for kernel errors
check_kernel_errors() {
    echo "--- Recent Kernel Errors ---"
    
    if command -v dmesg &> /dev/null; then
        error_count=$(dmesg | grep -i "error\|panic\|crash\|rcu.*stall" | tail -20 | wc -l)
        
        if [[ $error_count -gt 0 ]]; then
            echo -e "${RED}Found $error_count recent kernel errors:${NC}"
            dmesg | grep -i "error\|panic\|crash\|rcu.*stall" | tail -10
        else
            echo -e "${GREEN}✓ No recent kernel errors detected${NC}"
        fi
    else
        echo -e "${YELLOW}dmesg not available (requires root)${NC}"
    fi
    echo ""
}

# Function to check CPU usage
check_cpu_usage() {
    echo "--- CPU Usage ---"
    
    # Get 1-second average
    cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
    
    echo "CPU Usage: ${cpu_usage}%"
    
    # Check for high CPU processes
    echo ""
    echo "Top CPU-consuming processes:"
    ps aux --sort=-%cpu | head -6
    echo ""
}

# Run all checks
check_mpp_sessions
check_gstreamer_processes  
check_encoder_decoder_usage
check_memory
check_cpu_usage
check_kernel_errors

# Summary
echo "======================================"
echo " Health Check Summary"
echo "======================================"
echo ""

# Overall health determination
health_score=0

# Check session count
if [[ -f /sys/kernel/debug/mpp_service/session ]]; then
    session_count=$(cat /sys/kernel/debug/mpp_service/session | grep -c "session" || echo "0")
    if [[ $session_count -gt 8 ]]; then
        health_score=$((health_score + 3))
    elif [[ $session_count -gt 6 ]]; then
        health_score=$((health_score + 1))
    fi
fi

# Check memory
mem_available=$(free -m | awk 'NR==2 {print $7}')
mem_total=$(free -m | awk 'NR==2 {print $2}')
mem_percent=$((100 * mem_available / mem_total))
if [[ $mem_percent -lt 20 ]]; then
    health_score=$((health_score + 2))
elif [[ $mem_percent -lt 40 ]]; then
    health_score=$((health_score + 1))
fi

# Final verdict
if [[ $health_score -ge 4 ]]; then
    echo -e "${RED}Status: ❌ CRITICAL - System instability likely${NC}"
    echo "Recommendation: Stop some pipelines immediately"
    exit 2
elif [[ $health_score -ge 2 ]]; then
    echo -e "${YELLOW}Status: ⚠️  WARNING - System under stress${NC}"
    echo "Recommendation: Monitor closely, consider reducing load"
    exit 1
else
    echo -e "${GREEN}Status: ✓ HEALTHY - System operating normally${NC}"
    exit 0
fi
