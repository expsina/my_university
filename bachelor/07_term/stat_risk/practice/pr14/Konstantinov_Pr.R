df <- read_excel("12_18/gazp.xlsx")

colnames(df) <- c("tick", "per", "date", "time", "open", "high",
                  "low", "close", "vol", "rand")

View(df)

df["close_div_open"] <- df["close"] / df["open"]

cat("Average growth rate -- ", mean(df[["close_div_open"]]))
cat("Standard deviation of growth rate -- ", sd(df[["close_div_open"]]))

last_date <- max(df["date"])
open_fq <- df[df["date"] == 310724, ][["close"]]

s <- rnorm(10,
           mean = mean(df[["close_div_open"]]),
           sd = sd(df[["close_div_open"]]))

plot(cumprod(c(open_fq,s)),
     type='l',
     col="red",
     ylab="цена, руб.",
     xlab="день")

n <- 100000

generate.path <- function() {
  day <- 10
  s <- rnorm(10, mean = mean(df[["close_div_open"]]),
             sd = sd(df[["close_div_open"]]))
  sample_path <- cumprod(c(139.2,s))
  closing_price <- sample_path[day + 1]
  return(closing_price)
}

mc.closing <- replicate(n, generate.path())
q1=quantile(mc.closing,0.05) 
q3=quantile(mc.closing,0.95) 

print("нижняя граница цены", quote=FALSE)
print(q1, digits = 4)
print("верхняя граница цены", quote=FALSE)
print(q3, digits = 4)

median(mc.closing)
mean(mc.closing)
sd(mc.closing)

cat("Risk is", ((161 - 124) / median(mc.closing)) * 100)


pnorm(0, mean = 0.4, sd = 4.9) - pnorm(-100, mean = 0.4, sd = 4.9)
