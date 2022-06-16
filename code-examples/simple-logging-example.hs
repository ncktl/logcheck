-- https://riptutorial.com/haskell/example/29731/logging-with-hslogger
-- https://www.schoolofhaskell.com/user/eriks/Simple%20examples#integral
import           System.Log.Logger (Priority (DEBUG), debugM, infoM, setLevel,
                                    updateGlobalLogger, warningM)

list = [1, 2, 3, 4, 5]

main = do
  print list
  print $ head list
  debugM "MyProgram.main" "This won't be seen"
  infoM "MyProgram.main" "This won't be seen either"
  warningM "MyProgram.main" "This will be seen"