library(neuralnet)
library(knitr)
library(tidyverse)
library(caret)
library(ggplot2)
library(splines)
library(mgcv)
library(readxl)

reg_18 <- read_excel("reg_18.xlsx")

# взяли x2, x3, x8
# set <- sample(2:19, 3)
set <- c(3, 4, 9)

tfull <- reg_18[,c(set, 20)]
# взяли x2, x3, x8

fit_full <- lm(tfull$y ~ ., data = tfull)
summary(fit_full)

predictions <- fit_full %>% predict(tfull)
data.frame(
  RMSE = RMSE(predictions, tfull$y),
  R2 = R2(predictions, tfull$y)
)

optimal_fit <- step(fit_full, direction = "backward")
summary(optimal_fit)

predicions <- fit_full %>% predict(tfull)

data.frame(
  RMSE = RMSE(predictions, tfull$y),
  R2 = R2(predictions, tfull$y)
)

ggplot(tfull, aes(x = tfull$x2, y = tfull$y, col = "red")) +
  geom_point() + geom_smooth(method = "lm")


# метод главных компонент

hept_pca <- prcomp(tfull[, c(1, 2, 3)], scale = TRUE)
pc <- hept_pca$x
head(pc)
loadings <- hept_pca$rotation
head(loadings)

summary(hept_pca)

fit_full <- lm(tfull$y ~ pc[,1] + pc[,2])
summary(fit_full)


# множественная нелинейная регрессия

model <- lm(tfull$y ~ poly(tfull$x2, 2), data = tfull)
summary(model)

predictions <- model %>% predict(tfull)
data.frame(
  RMSE = RMSE(predictions, tfull$y),
  R2 = R2(predictions, tfull$y)
)


# сплайн-регрессия

knots <- quantile(tfull$x2, p = c(0.1, 0.5, 0.9))
model <- lm(tfull$y ~ bs(tfull$x2, knots = knots), data = tfull)
summary(model)

ggplot(tfull, aes(x2, y)) +
  geom_point() +
  stat_smooth(method = lm, formula = y ~ splines::bs(x, df = 3))

# обобщеные аддитивные модели

model <- gam(y ~ s(x2), data = tfull)
predictions <- model %>% predict(tfull)

data.frame(
  RMSE = RMSE(predictions, tfull$y),
  R2 = R2(predictions, tfull$y)
)

summary(model)

ggplot(tfull, aes(x2, y)) +
  geom_point() +
  stat_smooth(method = gam, formula = y ~ s(x))


# применяем нейросеть

data <- tfull[, 1:4]

apply(data, 2, function(x) sum(is.na(x)))

index <- sample(1:nrow(data), round(0.75 * nrow(data)))

train <- data[index, ]
test <- data[-index,]

lm.fit <- glm(train$y ~ ., data = train)
summary(lm.fit)

pr.lm <- predict(lm.fit, test)

MSE.lm <- sum((pr.lm - test$y) ^ 2) / nrow(test)
MSE.lm

maxs <- apply(data, 2, max)
mins <- apply(data, 2, min)
scaled <- as.data.frame(scale(data, center = mins, scale = maxs - mins))
train_ <- scaled[index, ]
test_ <- scaled[-index, ]

n <- names(train)
f <- as.formula(paste("y ~", paste(n[!n %in% "y"], collapse = "+")))

f

nn <- neuralnet(f, data = train_, hidden = c(5, 3), linear.output = TRUE)
plot(nn)

summary(nn)

pr.nn <- predict(nn, test_[,1:3])

pr.nn_ <- pr.nn * (max(data$y) - min(data$y) + min(data$y))
test.r <- (test_$y) * (max(data$y) - min(data$y) + min(data$y))
MSE.nn <- sum((test.r - pr.nn_)^2)/nrow(test_)
print(paste(MSE.lm, MSE.nn))

plot(test$y, pr.nn_, col="red", main="real vs predicted NN", pch = 18, cex = 0.7)
abline(0, 1, lwd=2)
legend("bottomright", legend = "NN", pch=18, col="red", bty="n")
plot(test$y, pr.lm, col="blue", main="real vs predicted lm", pch=18, cex=0.7)
abline(0,1,lwd=2)
legend("bottomright", legend="LM", pch=18, col="blue", bty="n", cex=.95)
