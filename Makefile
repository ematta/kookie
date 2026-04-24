.PHONY: install vendor test package check

install:
	npm --prefix extension install

vendor:
	npm --prefix extension run vendor

test:
	npm --prefix extension test

package:
	npm --prefix extension run package

check: vendor test
