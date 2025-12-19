#!/usr/bin/env node
// Test input validation functions
// Run with: node test-validation.js

console.log('====================================');
console.log('Input Validation Tests');
console.log('====================================\n');

let passed = 0;
let failed = 0;

// Copy validation functions from launcher.js
function validateIPAddress(ip) {
  const ipPattern = /^(\d{1,3}\.){3}\d{1,3}$/;
  if (!ipPattern.test(ip)) {
    return { valid: false, error: 'Invalid IP address format' };
  }
  
  const parts = ip.split('.');
  for (let part of parts) {
    const num = parseInt(part, 10);
    if (num < 0 || num > 255) {
      return { valid: false, error: 'IP address octets must be 0-255' };
    }
  }
  
  return { valid: true };
}

function validateRoomId(roomId) {
  if (!roomId || roomId.trim().length === 0) {
    return { valid: false, error: 'Room ID cannot be empty' };
  }
  
  if (roomId.length > 50) {
    return { valid: false, error: 'Room ID too long (max 50 characters)' };
  }
  
  const roomPattern = /^[a-zA-Z0-9_-]+$/;
  if (!roomPattern.test(roomId)) {
    return { valid: false, error: 'Room ID can only contain letters, numbers, dash, and underscore' };
  }
  
  return { valid: true };
}

function sanitizeInput(input) {
  return input.trim().replace(/[<>'"]/g, '');
}

function test(name, fn) {
  process.stdout.write(`Test: ${name}... `);
  try {
    fn();
    console.log('\x1b[32m✓ PASS\x1b[0m');
    passed++;
  } catch (e) {
    console.log('\x1b[31m✗ FAIL\x1b[0m');
    console.log(`  └─ ${e.message}`);
    failed++;
  }
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

// IP Address Tests
console.log('\n--- IP Address Validation ---\n');

test('Valid IP: 192.168.1.25', () => {
  const result = validateIPAddress('192.168.1.25');
  assert(result.valid === true, 'Should be valid');
});

test('Valid IP: 10.0.0.1', () => {
  const result = validateIPAddress('10.0.0.1');
  assert(result.valid === true, 'Should be valid');
});

test('Valid IP: 127.0.0.1', () => {
  const result = validateIPAddress('127.0.0.1');
  assert(result.valid === true, 'Should be valid');
});

test('Invalid IP: 999.999.999.999', () => {
  const result = validateIPAddress('999.999.999.999');
  assert(result.valid === false, 'Should be invalid');
  assert(result.error.includes('0-255'), 'Should mention range');
});

test('Invalid IP: 192.168.1', () => {
  const result = validateIPAddress('192.168.1');
  assert(result.valid === false, 'Should be invalid');
  assert(result.error.includes('format'), 'Should mention format');
});

test('Invalid IP: abc.def.ghi.jkl', () => {
  const result = validateIPAddress('abc.def.ghi.jkl');
  assert(result.valid === false, 'Should be invalid');
});

test('Invalid IP: 192.168.1.256', () => {
  const result = validateIPAddress('192.168.1.256');
  assert(result.valid === false, 'Should be invalid (256 > 255)');
});

test('Invalid IP: empty string', () => {
  const result = validateIPAddress('');
  assert(result.valid === false, 'Should be invalid');
});

// Room ID Tests
console.log('\n--- Room ID Validation ---\n');

test('Valid Room ID: r58studio', () => {
  const result = validateRoomId('r58studio');
  assert(result.valid === true, 'Should be valid');
});

test('Valid Room ID: test-room_123', () => {
  const result = validateRoomId('test-room_123');
  assert(result.valid === true, 'Should be valid');
});

test('Valid Room ID: UPPERCASE', () => {
  const result = validateRoomId('UPPERCASE');
  assert(result.valid === true, 'Should be valid');
});

test('Invalid Room ID: empty string', () => {
  const result = validateRoomId('');
  assert(result.valid === false, 'Should be invalid');
  assert(result.error.includes('empty'), 'Should mention empty');
});

test('Invalid Room ID: spaces only', () => {
  const result = validateRoomId('   ');
  assert(result.valid === false, 'Should be invalid');
});

test('Invalid Room ID: special chars @#$', () => {
  const result = validateRoomId('room@test#123$');
  assert(result.valid === false, 'Should be invalid');
  assert(result.error.includes('letters'), 'Should mention allowed chars');
});

test('Invalid Room ID: too long (51 chars)', () => {
  const result = validateRoomId('a'.repeat(51));
  assert(result.valid === false, 'Should be invalid');
  assert(result.error.includes('long'), 'Should mention length');
});

test('Invalid Room ID: with spaces', () => {
  const result = validateRoomId('room with spaces');
  assert(result.valid === false, 'Should be invalid');
});

// Sanitization Tests
console.log('\n--- Input Sanitization ---\n');

test('Sanitize: removes <script> tags', () => {
  const result = sanitizeInput('<script>alert("xss")</script>');
  assert(!result.includes('<'), 'Should remove <');
  assert(!result.includes('>'), 'Should remove >');
});

test('Sanitize: removes quotes', () => {
  const result = sanitizeInput('test"with\'quotes');
  assert(!result.includes('"'), 'Should remove double quotes');
  assert(!result.includes("'"), 'Should remove single quotes');
});

test('Sanitize: trims whitespace', () => {
  const result = sanitizeInput('  test  ');
  assert(result === 'test', 'Should trim whitespace');
});

test('Sanitize: keeps safe characters', () => {
  const result = sanitizeInput('test-room_123');
  assert(result === 'test-room_123', 'Should keep safe chars');
});

// Edge Cases
console.log('\n--- Edge Cases ---\n');

test('IP: leading zeros (010.0.0.1)', () => {
  const result = validateIPAddress('010.0.0.1');
  // This is actually valid (010 = 10)
  assert(result.valid === true, 'Should handle leading zeros');
});

test('Room ID: single character', () => {
  const result = validateRoomId('a');
  assert(result.valid === true, 'Should allow single char');
});

test('Room ID: 50 characters (max)', () => {
  const result = validateRoomId('a'.repeat(50));
  assert(result.valid === true, 'Should allow exactly 50 chars');
});

test('Sanitize: empty string', () => {
  const result = sanitizeInput('');
  assert(result === '', 'Should handle empty string');
});

// Summary
console.log('\n====================================');
console.log('Test Results');
console.log('====================================\n');
console.log(`Total:  ${passed + failed}`);
console.log(`\x1b[32mPassed: ${passed}\x1b[0m`);
console.log(`\x1b[31mFailed: ${failed}\x1b[0m\n`);

if (failed === 0) {
  console.log('\x1b[32m✓ ALL VALIDATION TESTS PASSED\x1b[0m\n');
  process.exit(0);
} else {
  console.log('\x1b[31m✗ SOME TESTS FAILED\x1b[0m\n');
  process.exit(1);
}
