
import sys,os
import captcha

def run_one_test(basedir, **kw):
    guesser=captcha.Guesser(basedir+"/iconset",**kw)

    correctcount = 0
    wrongcount = 0
    for i in os.listdir(basedir+'/examples'):
        code=guesser.guess(basedir+'/examples/'+i)
        correct_code=i.split(".")[0]
        if code==correct_code:
            correctcount += 1
            msg="ok"
        else:
            wrongcount += 1
            msg="*** FAIL"
        print "%s: expected is %-7s actual is %-7s %s"%(i,correct_code,code,msg)

    print "======================="
    correctcount = float(correctcount)
    wrongcount = float(wrongcount)
    print "Correct Guesses - %d"%correctcount
    print "Wrong Guesses - %d"%wrongcount
    print "Percentage Correct - ", correctcount/(correctcount+wrongcount)*100.00
    print "Percentage Wrong - ", wrongcount/(correctcount+wrongcount)*100.00

run_one_test("test_data/set1",
             minimal_letter_width=1,
             minimal_letter_height=1,
             minimal_number_of_set_pixel_per_line=1,
             should_be_black=lambda pix:pix ==220 or pix==227,
             minimal_similarity=0.0)

run_one_test("test_data/set2")
