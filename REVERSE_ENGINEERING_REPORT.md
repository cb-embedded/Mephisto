
================================================================================
8051 SOUND CPU - ANNOTATED DISASSEMBLY
Binary: sound_cpu_8051.bin
Purpose: UART-to-AY-3-8910 interface
================================================================================

INTERRUPT VECTOR TABLE (0x0000 - 0x002B)
----------------------------------------
0000: 02 00 26     LJMP 0x0026           ; Reset vector -> initialization
0003: 02 06 1F     LJMP 0x061F           ; EXT0 interrupt -> error handler
000B: 02 05 1D     LJMP 0x051D           ; Timer 0 interrupt -> timer handler
0013: 02 06 1F     LJMP 0x061F           ; EXT1 interrupt -> error handler
001B: 02 06 1F     LJMP 0x061F           ; Timer 1 interrupt -> error handler
0023: 02 04 45     LJMP 0x0445           ; UART interrupt -> CRITICAL!


INITIALIZATION ROUTINE (0x0026)
-------------------------------
0026: 75 81 57     MOV SP,#0x57          ; Set stack pointer
0029: 75 A8 00     MOV IE,#0x00          ; Disable interrupts initially
002C: 75 D0 00     MOV PSW,#0x00         ; Clear program status word
002F: 75 90 FF     MOV P1,#0xFF          ; Set P1 (AY bus) to idle state
0032: 75 A0 FF     MOV P2,#0xFF          ; Set P2 to 0xFF
0035: 75 80 FF     MOV P0,#0xFF          ; Set P0 to 0xFF
0038: 75 B0 FF     MOV P3,#0xFF          ; Set P3 to 0xFF
003B: 7B 00        MOV R3,#0x00          ; Clear R3
003D: 78 7F        MOV R0,#0x7F          ; R0 = 0x7F

; RAM initialization loop
003F: E8           MOV A,R0
0040: F4           CPL A                 ; Complement A
0041: F6           MOV @R0,A            ; Store to RAM
0042: D8 FB        DJNZ R0,0x003F       ; Loop for all RAM

; RAM test
0044: 78 7F        MOV R0,#0x7F
0046: E8           MOV A,R0
0047: 66           ???                   ; XRL A,@R0 equivalent
0048: 04           INC A
0049: 60 05        JZ 0x0050            ; If zero, RAM OK
004B: 74 01        MOV A,#0x01
004D: 02 06 1F     LJMP 0x061F          ; Error if RAM test fails

; Continue initialization...
0050: F6           MOV @R0,A
0051: D8 F3        DJNZ R0,0x0046

; More RAM clearing
0053: 90 00 00     MOV DPTR,#0x0000
0056: 78 08        MOV R0,#0x08
0058: 79 FF        MOV R1,#0xFF
005A: E9           MOV A,R1
005B: F0           MOVX @DPTR,A         ; Clear external RAM
005C: A3           INC DPTR
005D: D9 FB        DJNZ R1,0x005A
005F: E9           MOV A,R1
0060: F0           MOVX @DPTR,A
0061: A3           INC DPTR
0062: D8 F4        DJNZ R0,0x0058

; Initialize UART
0092: 75 81 56     MOV SP,#0x56          ; Adjust stack pointer
0095: 12 03 32     LCALL 0x0332          ; Call UART setup function
0098: 12 04 1B     LCALL 0x041B          ; Call timer setup function


MAIN LOOP (0x009E - 0x00C0)
---------------------------
009E: C2 09        CLR bit_09            ; Clear status bit
00A0: A2 09        MOV C,bit_09
00A2: 92 B3        MOV bit_B3,C          ; Update UART bit
00A4: 75 D0 00     MOV PSW,#0x00
00A7: C2 04        CLR bit_04            ; Clear data ready flag

; Wait for UART data
00A9: 12 02 21     LCALL 0x0221          ; Delay function
00AC: 30 04 FA     JNB bit_04,0x00A9     ; Loop until data ready
00AF: D2 09        SETB bit_09
00B1: A2 09        MOV C,bit_09
00B3: 92 B3        MOV bit_B3,C

; Process received command
00B6: 12 01 D8     LCALL 0x01D8          ; Call command buffer check
00B9: 60 07        JZ 0x00C2             ; If zero, no command
00BB: 74 A0        MOV A,#0xA0
00BD: 12 02 22     LCALL 0x0222          ; Check if command is 0xA0
00C0: 80 DD        SJMP 0x009E           ; Loop back

; Check for command type 0xB6 marker
00C2: 74 B0        MOV A,#0xB0
00C4: 12 02 22     LCALL 0x0222          ; Check if end marker
00C7: 30 0D 0A     JNB bit_0D,0x00D4     ; If not set, continue
00CA: 90 00 4F     MOV DPTR,#0x004F      ; Point to command marker location
00CD: E0           MOVX A,@DPTR          ; Read command marker
00CE: B4 B6 03     CJNE A,#0xB6,0x00D4   ; Compare with 0xB6
00D1: 02 00 9E     LJMP 0x009E           ; If match, restart loop


COMMAND PROCESSING (0x00E0 onwards)
-----------------------------------
; Main command dispatcher reads bytes from buffer at 0x0050
; and dispatches based on command type

00E0: 90 00 50     MOV DPTR,#0x0050      ; Point to data buffer
00E3: E0           MOVX A,@DPTR          ; Read first data byte
00E4: F9           MOV R1,A              ; Save to R1
00E5: 19           DEC R1                ; Decrement (make 0-based?)
00E6: 19           DEC R1                ; Decrement again
00E7: 75 27 00     MOV 0x27,#0x00        ; Clear variable

; Process each byte in buffer
00EA: 85 27 A0     MOV P2,0x27           ; Use 0x27 as index
00ED: 74 50        MOV A,#0x50           ; Base address 0x50
00EF: 2C           ADD A,R4              ; Add offset
00F0: F8           MOV R0,A              ; R0 = pointer
00F1: E2           MOVX A,@R0            ; Read from buffer
00F2: F5 F0        MOV 0xF0,A            ; Save to temp

; Check command type
00F4: C3           CLR C
00F5: 94 A0        SUBB A,#0xA0          ; Compare with 0xA0
00F7: 50 09        JNC 0x0102            ; If >= 0xA0, continue
00F9: AB F0        MOV R3,0xF0
00FB: 12 02 2F     LCALL 0x022F          ; Process non-command byte
00FE: 19           DEC R1
00FF: 0C           INC R4
0100: 21 B0        AJMP 0x01B0           ; Continue

; Command 0xA2 - Set Frequency Low
0102: E5 F0        MOV A,0xF0
0104: B4 A2 06     CJNE A,#0xA2,0x010D   ; Is it 0xA2?
0107: 05 29        INC 0x29              ; Yes - increment counter
0109: 0C           INC R4
010A: 19           DEC R1
010B: 21 B0        AJMP 0x01B0

; Command 0xA3 - Set Frequency High
010D: E5 F0        MOV A,0xF0
010F: B4 A3 06     CJNE A,#0xA3,0x0118   ; Is it 0xA3?
0112: 05 2A        INC 0x2A              ; Yes - increment counter
0114: 0C           INC R4
0115: 19           DEC R1
0116: 21 B0        AJMP 0x01B0

; Command 0xA4 - Multi-byte command (channel + freq + amplitude)
0118: E5 F0        MOV A,0xF0
011A: 54 F0        ANL A,#0xF0           ; Mask upper nibble
011C: B4 A4 25     CJNE A,#0xA4,0x0144   ; Is it 0xA4?
011F: E5 F0        MOV A,0xF0
0121: 54 0F        ANL A,#0x0F           ; Get lower nibble (channel?)
0123: 10 E3 0F     JBC bit_E3,0x0135     ; Check bit
0126: AA 2B        MOV R2,0x2B
0128: CA           XCH A,R2
0129: C3           CLR C
012A: 9A           SUBB A,R2
012B: F5 2B        MOV 0x2B,A            ; Store result
012D: 90 00 72     MOV DPTR,#0x0072      ; Point to data location
0130: F0           MOVX @DPTR,A          ; Store value
0131: 0C           INC R4
0132: 19           DEC R1
0133: 21 B0        AJMP 0x01B0

0135: AA 2C        MOV R2,0x2C
0137: CA           XCH A,R2
0138: C3           CLR C
0139: 9A           SUBB A,R2
013A: F5 2C        MOV 0x2C,A
013C: 90 00 73     MOV DPTR,#0x0073      ; Point to data location
013F: F0           MOVX @DPTR,A          ; Store value
0140: 0C           INC R4
0141: 19           DEC R1
0142: 21 B0        AJMP 0x01B0

; Command 0xA6 - Stop/Reset
0144: E5 F0        MOV A,0xF0
0146: B4 A6 7D     CJNE A,#0xA6,0x01C6   ; Is it 0xA6?
0149: C2 0B        CLR bit_0B            ; Clear processing flag
014B: C2 0C        CLR bit_0C            ; Clear UART flag
014D: 90 00 6E     MOV DPTR,#0x006E
0150: 74 A7        MOV A,#0xA7           ; Load 0xA7
0152: F0           MOVX @DPTR,A          ; Store to memory


UART INTERRUPT HANDLER (0x0445) - CRITICAL!
-------------------------------------------
; This is the heart of the UART reception

0445: C0 D0        PUSH PSW              ; Save context
0447: C0 E0        PUSH 0xE0             ; Save accumulator
0449: C0 82        PUSH 0x82             ; Save DPL
044B: C0 83        PUSH 0x83             ; Save DPH
044D: C0 27        PUSH 0x27             ; Save R7
044F: D2 B3        SETB bit_B3           ; Set transmit bit

0451: 20 99 09     JB bit_99,0x045D      ; Check UART RI flag
0454: 12 04 70     LCALL 0x0470          ; Call receive handler
0457: D2 0C        SETB bit_0C           ; Set receive complete flag
0459: C2 98        CLR bit_98            ; Clear SCON.0 (RI)
045B: 80 04        SJMP 0x0461           ; Skip transmit part

045D: D2 0B        SETB bit_0B           ; Handle transmit
045F: C2 99        CLR bit_99            ; Clear TI flag

0461: D0 27        POP 0x27              ; Restore context
0463: D0 83        POP 0x83
0465: D0 82        POP 0x82
0467: D0 E0        POP 0xE0
0469: A2 09        MOV C,bit_09
046B: 92 B3        MOV bit_B3,C
046D: D0 D0        POP PSW
046F: 32           RETI                  ; Return from interrupt


UART RECEIVE HANDLER (0x0470) - COMMAND PARSER
----------------------------------------------
0470: 30 04 01     JNB bit_04,0x0474     ; Check if busy
0473: 22           RET                   ; Return if busy

0474: C0 E0        PUSH 0xE0             ; Save context
0476: C0 83        PUSH 0x83
0478: C0 82        PUSH 0x82
047A: C0 F0        PUSH 0xF0

047C: 90 00 4B     MOV DPTR,#0x004B      ; Point to state variable
047F: E0           MOVX A,@DPTR          ; Read state
0480: 25 E0        ADD A,0xE0            ; Multiply by 2 (for jump table)
0482: 90 04 86     MOV DPTR,#0x0486      ; Point to jump table
0485: 73           JMP @A+DPTR           ; Jump to state handler!

; Jump table at 0x0486:
0486: 81 8C        AJMP 0x048C           ; State 0: Wait for start byte
0488: 81 BB        AJMP 0x04BB           ; State 1: Receive data bytes
048A: 81 DE        AJMP 0x04DE           ; State 2: Process command

; State 0: Check for start marker (0xB5 or 0xB6)
048C: E5 99        MOV A,SBUF            ; *** READ FROM UART! ***
048E: B4 B5 02     CJNE A,#0xB5,0x0493   ; Is it 0xB5?
0491: 80 03        SJMP 0x0496           ; Yes, accept it

0493: B4 B6 13     CJNE A,#0xB6,0x04A9   ; Is it 0xB6?
                                         ; If not, ignore byte

; Start marker detected!
0496: 90 00 4F     MOV DPTR,#0x004F      ; Point to marker storage
0499: F0           MOVX @DPTR,A          ; Store marker (0xB5 or 0xB6)
049A: 90 00 4B     MOV DPTR,#0x004B      ; Point to state
049D: 74 01        MOV A,#0x01           ; Set state = 1
049F: F0           MOVX @DPTR,A          ; Store new state
04A0: D0 F0        POP 0xF0              ; Restore context
04A2: D0 82        POP 0x82
04A4: D0 83        POP 0x83
04A6: D0 E0        POP 0xE0
04A8: 22           RET                   ; Return

; If not start marker, stay in state 0
04A9: 90 00 4B     MOV DPTR,#0x004B
04AC: 74 00        MOV A,#0x00           ; State = 0
04AE: F0           MOVX @DPTR,A
04AF: D0 F0        POP 0xF0
04B1: D0 82        POP 0x82
04B3: D0 83        POP 0x83
04B5: D0 E0        POP 0xE0
04B7: 22           RET

; Jump to here for unknown opcode (error handler)
04B8: 02 06 1F     LJMP 0x061F

; State 1: Receive data bytes into buffer
04BB: E5 99        MOV A,SBUF            ; *** READ FROM UART! ***
04BD: 90 00 50     MOV DPTR,#0x0050      ; Point to buffer start
04C0: F0           MOVX @DPTR,A          ; Store first byte
04C1: 90 00 4E     MOV DPTR,#0x004E      ; Another storage location
04C4: F0           MOVX @DPTR,A
04C5: 90 00 4B     MOV DPTR,#0x004B      ; Point to state
04C8: 74 02        MOV A,#0x02           ; Set state = 2
04CA: F0           MOVX @DPTR,A
04CB: 90 00 4C     MOV DPTR,#0x004C      ; Point to buffer pointer
04CE: 74 51        MOV A,#0x51           ; Next buffer location
04D0: F0           MOVX @DPTR,A
04D1: A3           INC DPTR
04D2: 74 00        MOV A,#0x00
04D4: F0           MOVX @DPTR,A
04D5: D0 F0        POP 0xF0
04D7: D0 82        POP 0x82
04D9: D0 83        POP 0x83
04DB: D0 E0        POP 0xE0
04DD: 22           RET

; State 2: Continue receiving multi-byte command
04DE: 90 00 4C     MOV DPTR,#0x004C      ; Get buffer pointer
04E1: E0           MOVX A,@DPTR
04E2: F5 F0        MOV 0xF0,A            ; Save low byte
04E4: A3           INC DPTR
04E5: E0           MOVX A,@DPTR          ; Get high byte
04E6: 85 F0 82     MOV 0x82,0xF0         ; Set up DPTR for write
04E9: F5 83        MOV 0x83,A
04EB: E5 99        MOV A,SBUF            ; *** READ FROM UART! ***
04ED: F0           MOVX @DPTR,A          ; Store to buffer
04EE: A3           INC DPTR              ; Increment pointer
04EF: 85 83 F0     MOV 0xF0,0x83
04F2: E5 82        MOV A,0x82
04F4: 90 00 4C     MOV DPTR,#0x004C      ; Update stored pointer
04F7: F0           MOVX @DPTR,A
04F8: A3           INC DPTR
04F9: E5 F0        MOV A,0xF0
04FB: F0           MOVX @DPTR,A

04FC: 90 00 4E     MOV DPTR,#0x004E      ; Check byte count
04FF: E0           MOVX A,@DPTR
0500: 14           DEC A                 ; Decrement counter
0501: F0           MOVX @DPTR,A
0502: 60 09        JZ 0x050D             ; If zero, done

0504: D0 F0        POP 0xF0              ; Not done yet, restore and return
0506: D0 82        POP 0x82
0508: D0 83        POP 0x83
050A: D0 E0        POP 0xE0
050C: 22           RET

; All bytes received, signal main loop
050D: D2 04        SETB bit_04           ; Set data ready flag!
050F: 90 00 4B     MOV DPTR,#0x004B
0512: E4           CLR A                 ; Set state = 0
0513: F0           MOVX @DPTR,A
0514: D0 F0        POP 0xF0
0516: D0 82        POP 0x82
0518: D0 83        POP 0x83
051A: D0 E0        POP 0xE0
051C: 22           RET


AY-3-8910 CONTROL FUNCTIONS (0x05A6 onwards)
--------------------------------------------
; These functions write to the AY-3-8910 PSG chip

05A6: 75 90 0F     MOV P1,#0x0F          ; Set control lines
05A9: 43 B0 30     ORL P3,#0x30          ; Set BC1/BC2 bits
05AC: 53 B0 CF     ANL P3,#0xCF          ; Clear BDIR
05AF: 75 90 FF     MOV P1,#0xFF          ; Set data lines high
05B2: 43 B0 20     ORL P3,#0x20          ; Set BC2
05B5: 85 90 44     MOV 0x44,P1           ; Read back P1
05B8: 53 B0 CF     ANL P3,#0xCF          ; Clear control

; This appears to be a register write sequence
05BB: 75 27 00     MOV 0x27,#0x00
05BE: 85 27 A0     MOV P2,0x27           ; Use as index
05C1: 74 74        MOV A,#0x74
05C3: 25 41        ADD A,0x41            ; Add offset
05C5: F8           MOV R0,A
05C6: E5 44        MOV A,0x44            ; Get previous P1 value
05C8: F2           MOVX @R0,A            ; Store it
05C9: 05 41        INC 0x41              ; Increment register
05CB: E5 41        MOV A,0x41
05CD: C3           CLR C
05CE: 94 05        SUBB A,#0x05          ; Check if done 5 registers
05D0: 40 03        JC 0x05D5             ; If not, continue
05D2: 75 41 00     MOV 0x41,#0x00        ; Reset counter

05D5: E5 41        MOV A,0x41
05D7: 90 05 E1     MOV DPTR,#0x05E1      ; Point to table
05DA: 93           MOVC A,@A+DPTR        ; Look up value
05DB: 53 43 06     ANL 0x43,#0x06        ; Mask bits
05DE: 42 43        ORL 0x43,A            ; Combine
05E0: 22           RET

; Control bit table
05E1: 08 10 20 40 80                      ; Bit patterns


05E6: 75 90 0E     MOV P1,#0x0E          ; Another control sequence
05E9: 43 B0 30     ORL P3,#0x30
05EC: 53 B0 CF     ANL P3,#0xCF
05EF: 85 43 90     MOV P1,0x43           ; Write register value!
05F2: 43 B0 10     ORL P3,#0x10
05F5: 53 B0 CF     ANL P3,#0xCF
05F8: 22           RET                   ; Return


TIMER INTERRUPT HANDLER (0x051D)
--------------------------------
051D: C0 A8        PUSH IE
051F: C0 E0        PUSH 0xE0
0521: C0 D0        PUSH PSW
0523: C0 F0        PUSH 0xF0
0525: C0 82        PUSH 0x82
0527: C0 83        PUSH 0x83
0529: C0 27        PUSH 0x27
052B: D2 B3        SETB bit_B3
052D: C0 D0        PUSH PSW
052F: C2 AF        CLR EA                ; Disable interrupts

0531: 12 05 87     LCALL 0x0587          ; Call timer service routine
0534: D0 D0        POP PSW
0536: 05 28        INC 0x28              ; Increment timer counter
0538: E5 28        MOV A,0x28
053A: B4 64 24     CJNE A,#0x64,0x0561   ; Compare with 100 (0x64)
053D: 75 28 00     MOV 0x28,#0x00        ; Reset if reached 100

0540: 20 08 1E     JB bit_08,0x0561      ; Check flag
0543: D2 08        SETB bit_08           ; Set flag
0545: D2 AF        SETB EA               ; Enable interrupts

0547: 75 D0 08     MOV PSW,#0x08         ; Switch register bank
054A: 12 05 74     LCALL 0x0574          ; Call function
054D: 12 02 3D     LCALL 0x023D          ; Call function
0550: 12 05 A6     LCALL 0x05A6          ; Call AY write function!
0553: 12 05 F9     LCALL 0x05F9          ; Call function
0556: 12 05 E6     LCALL 0x05E6          ; Call AY control!
0559: 12 24 08     LCALL 0x2408          ; Call function
055C: 12 07 A3     LCALL 0x07A3          ; Call function
055F: C2 08        CLR bit_08            ; Clear flag

0561: D0 27        POP 0x27              ; Restore context
0563: D0 83        POP 0x83
0565: D0 82        POP 0x82
0567: D0 F0        POP 0xF0
0569: A2 09        MOV C,bit_09
056B: 92 B3        MOV bit_B3,C
056D: D0 D0        POP PSW
056F: D0 E0        POP 0xE0
0571: D0 A8        POP IE
0573: 22           RET


================================================================================
SUMMARY OF KEY FINDINGS
================================================================================

UART COMMAND PROTOCOL:
---------------------
1. Start Marker: 0xB5 or 0xB6
   - Detected in UART handler at 0x048C
   - Triggers state machine to state 1

2. Command Byte: One of the following
   - 0xA0: Status/simple command
   - 0xA2: Set frequency low byte
   - 0xA3: Set frequency high byte  
   - 0xA4: Full note command (channel + freq + amplitude)
   - 0xA6: Stop/silence command
   - 0xA7: Special command
   - 0xA8: Another special command

3. Data Bytes: Variable length depending on command
   - Stored in buffer starting at 0x0050
   - State machine in UART handler manages reception

4. End Marker: 0xB0
   - Detected in main loop at 0x01AB
   - Signals end of command sequence

AY-3-8910 INTERFACE:
-------------------
- Port P1 (0x90): 8-bit data/address bus to AY chip
- Port P3 bits: Control signals (BC1, BC2, BDIR)
- Functions at 0x05A6 and 0x05E6 handle register writes
- Timer interrupt drives periodic AY updates (0x051D)

STATE MACHINE:
-------------
State 0: Wait for start marker (0xB5 or 0xB6)
State 1: Receive first command/data byte
State 2: Continue receiving multi-byte command
On completion: Set bit_04 flag, return to state 0

Main loop polls bit_04 flag and processes complete commands

