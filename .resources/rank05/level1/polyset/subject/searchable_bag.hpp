#pragma once

#include "bag.hpp"

class searchable_bag : virtual public bag {
public:
    virtual ~searchable_bag() {}
    virtual bool has(int) const = 0;
};
