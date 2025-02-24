from vega.common.class_factory import ClassFactory


ClassFactory.lazy_register("vega.algorithms.fully_train", {
    "resnet.resnet_trainer_callback": ["trainer:ResnetTrainer"]
})
