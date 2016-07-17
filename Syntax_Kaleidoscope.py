# LiuTaoTao github.com/Bookaa/LiuD

SynName = 'ks'

ignores = {
    'crlf'   : ( ' \t\n', [ r'/\*(.|\n)*?\*/' ] ),
    'wspace' : ( ' \t',   [ r'/\*(.|\n)*?\*/' ] ),
    'no'     : ( '', [] )
}

base_def = { 'NEWLINE' :    ('',   '\\n+'),
             'NAME'    :    ('Name',  '[A-Za-z_][A-Za-z0-9_]*'),
             'NUMBER_INT' : ('Int',     r'0|[1-9]\d*'),
             'NUMBER_DOUBLE' :  ('Double',  r'\d+\.\d+')
             }

s_tree = '''
.set_linecomment '\#'

.syntax crlf
Module(vlst*) : stmt* ENDMARKER$
params : value ^+ ','
forbody : forbody1 | cmd
forbody1 : '(' body ')'
body : cmd ^* ':'
enclosed : '(' value ')'
cmd :: funccall | ifcmd | forcmd | value
funccall : NAME '(' params? ')'
funcdef : 'def' NAME '(' arg* ')' body

stmtone :: funcdef | funccall


arg : NAME


value(v1,s,v2): item3 ^- ('*' ('+'|'-') ('>'|'<'|'!='|'==') '|')
    item3 :: negitem | item1
    negitem : '-' item1
    item1 :: funccall | forcmd | litNumf | litNumi | enclosed | litVarname 
    litVarname : NAME
    litNumi : NUMBER_INT
    litNumf : NUMBER_DOUBLE


ifcmd : 'if' value 'then' body elseclause* 'else' body

elseclause : 'else' 'if' value 'then' body

forcmd : 'for' assigncmd ',' condi ',' step 'in' forbody
    condi :: value
    step :: value
    assigncmd : NAME '=' value


.syntax wspace
stmt :: stmtone NEWLINE$

'''

Out_self = '''
Module : (x NL)*
stmtone : x
funccall : x '(' x? ')'
arg : x 
params : x ^* ','
value : x x x
assigncmd : x '=' x
negitem : '-' x
enclosed : '(' x ')'
litVarname : x
litNumi : x
litNumf : x
funcdef : 'def' x '(' x* ')' x
body : x ^* ':'
ifcmd : 'if' x 'then' x x* 'else' x
elseclause : 'else if' x 'then' x
forcmd : 'for' x ',' x ',' x 'in' x
forbody : x
forbody1 : '(' x ')'
'''

s_sample = '''
# def unary- (v) 0 - v

# def binary> 10 (lhs rhs) rhs < lhs

# def binary: 1 (x y) y

# def binary| 5 (lhs rhs)
#    if lhs then 1 else if rhs then 1 else 0

def printdensity(d)
    if d > 8 then
        putchard(32) # ' '
    else if d > 4 then
        putchard(46) # '.'
    else if d > 2 then
        putchard(43) # '+'
    else
        putchard(42) # '*'

def mandelconverger(real imag iters creal cimag)
    if iters > 255 | (real*real + imag*imag > 4) then
        iters
    else
        mandelconverger(real*real - imag*imag + creal,
                        2*real*imag + cimag,
                        iters+1, creal, cimag)

def mandelconverge(real imag)
    mandelconverger(real, imag, 0, real, imag)

def mandelhelp(xmin xmax xstep ymin ymax ystep)
    for y = ymin, y < ymax, ystep in ( 
        ( for x = xmin, x < xmax, xstep in
            printdensity(mandelconverge(x, y)))
        : putchard(10))

def mandel(realstart imagstart realmag imagmag)
    mandelhelp(realstart, realstart+realmag*78, realmag,
               imagstart, imagstart+imagmag*48, imagmag)

mandel(-2.3, -1.3, 0.05, 0.07)
'''
